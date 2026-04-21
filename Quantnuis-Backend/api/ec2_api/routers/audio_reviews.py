#!/usr/bin/env python3
"""
================================================================================
                    EC2 API - AUDIO REVIEWS ROUTER
================================================================================

Endpoints pour la revue des prédictions IA sur les fichiers audio S3.

- POST /audio-reviews/scan     : Scan S3 + analyse IA des nouveaux fichiers (admin)
- GET  /audio-reviews          : Liste paginée des revues (user)
- GET  /audio-reviews/stats    : Statistiques des revues (user)
- PATCH /audio-reviews/{id}    : Valider/corriger une revue (user)

================================================================================
"""

import logging
from datetime import datetime

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from config import get_settings
from database import get_db, User, AudioReview, ReviewStatus, s3_audio_manager
from database.schemas import (
    AudioReviewResponse, AudioReviewListResponse,
    AudioReviewValidation, AudioReviewStats,
)
from ..dependencies import get_current_user, get_admin_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/audio-reviews", tags=["audio-reviews"])
settings = get_settings()


# ==============================================================================
# BACKGROUND TASK: SCAN & ANALYZE
# ==============================================================================

async def _scan_and_analyze(new_keys: list[str], db_url: str):
    """
    Background task: download each new audio from S3 via presigned URL,
    send to Lambda /predict, and store the result in DB.
    """
    import httpx
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    engine = create_engine(db_url)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            for s3_key in new_keys:
                try:
                    # 1. Get presigned URL for this file
                    presigned_url = s3_audio_manager.get_presigned_url(s3_key)

                    # 2. Download the audio file
                    download_resp = await client.get(presigned_url)
                    download_resp.raise_for_status()
                    audio_bytes = download_resp.content

                    # 3. Determine filename from s3_key
                    filename = s3_key.split("/")[-1]

                    # 4. Send to Lambda /predict
                    predict_resp = await client.post(
                        f"{settings.LAMBDA_PREDICT_URL}/predict",
                        files={"file": (filename, audio_bytes, "audio/wav")},
                    )
                    predict_resp.raise_for_status()
                    result = predict_resp.json()

                    # 5. Parse the _full_result (Lambda returns nested format)
                    full = result.get("_full_result", result)

                    car_detected = full.get("car_detected", False)
                    car_confidence = full.get("car_confidence", 0.0)
                    car_probability = full.get("car_probability", 0.0)

                    is_noisy = full.get("is_noisy")
                    noisy_confidence = full.get("noisy_confidence")
                    noisy_probability = full.get("noisy_probability")

                    # 6. Store in DB
                    review = AudioReview(
                        s3_key=s3_key,
                        car_detected=car_detected,
                        car_confidence=car_confidence,
                        car_probability=car_probability,
                        is_noisy=is_noisy,
                        noisy_confidence=noisy_confidence,
                        noisy_probability=noisy_probability,
                        review_status=ReviewStatus.PENDING,
                        analyzed_at=datetime.utcnow(),
                    )
                    db.add(review)
                    db.commit()
                    logger.info(f"Analyzed {s3_key}: car={car_detected}, noisy={is_noisy}")

                except Exception as e:
                    logger.error(f"Failed to analyze {s3_key}: {e}")
                    db.rollback()
                    continue
    finally:
        db.close()


# ==============================================================================
# ENDPOINTS
# ==============================================================================

@router.post("/scan")
async def scan_new_files(
    background_tasks: BackgroundTasks,
    admin: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    """
    Scan S3 for new audio files and analyze them via Lambda (admin only).

    Returns immediately with the count of new files queued for analysis.
    """
    # 1. List all audio files in S3
    s3_files = s3_audio_manager.list_audio_files(max_files=500)
    all_keys = [f.key for f in s3_files]

    # 2. Get already-analyzed keys from DB
    existing_keys = {
        row[0]
        for row in db.query(AudioReview.s3_key).all()
    }

    # 3. Filter new files
    new_keys = [k for k in all_keys if k not in existing_keys]

    if not new_keys:
        return {"message": "Aucun nouveau fichier a analyser", "new_files": 0}

    # 4. Launch background analysis
    background_tasks.add_task(
        _scan_and_analyze,
        new_keys,
        str(settings.DATABASE_URL),
    )

    return {
        "message": f"{len(new_keys)} fichier(s) en cours d'analyse",
        "new_files": len(new_keys),
        "total_s3": len(all_keys),
        "already_analyzed": len(existing_keys),
    }


@router.get("", response_model=AudioReviewListResponse)
async def list_reviews(
    status_filter: str = Query("all", description="Filter: all/pending/confirmed/corrected"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List audio reviews with pagination and optional status filter."""
    query = db.query(AudioReview)

    if status_filter != "all":
        query = query.filter(AudioReview.review_status == status_filter)

    total = query.count()
    reviews = (
        query.order_by(AudioReview.analyzed_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    # Generate presigned URLs for each audio file
    review_responses = []
    for r in reviews:
        audio_url = None
        try:
            audio_url = s3_audio_manager.get_presigned_url(r.s3_key)
        except Exception:
            pass

        review_responses.append(
            AudioReviewResponse(
                id=r.id,
                s3_key=r.s3_key,
                car_detected=r.car_detected,
                car_confidence=r.car_confidence,
                car_probability=r.car_probability,
                is_noisy=r.is_noisy,
                noisy_confidence=r.noisy_confidence,
                noisy_probability=r.noisy_probability,
                review_status=r.review_status,
                reviewer_comment=r.reviewer_comment,
                analyzed_at=r.analyzed_at,
                reviewed_at=r.reviewed_at,
                audio_url=audio_url,
            )
        )

    return AudioReviewListResponse(
        reviews=review_responses,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/stats", response_model=AudioReviewStats)
async def get_review_stats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get audio review statistics."""
    total = db.query(AudioReview).count()
    pending = db.query(AudioReview).filter(
        AudioReview.review_status == ReviewStatus.PENDING
    ).count()
    confirmed = db.query(AudioReview).filter(
        AudioReview.review_status == ReviewStatus.CONFIRMED
    ).count()
    corrected = db.query(AudioReview).filter(
        AudioReview.review_status == ReviewStatus.CORRECTED
    ).count()

    reviewed = confirmed + corrected
    accuracy_rate = (confirmed / reviewed * 100) if reviewed > 0 else None

    return AudioReviewStats(
        total=total,
        pending=pending,
        confirmed=confirmed,
        corrected=corrected,
        accuracy_rate=accuracy_rate,
    )


@router.patch("/{review_id}")
async def validate_review(
    review_id: int,
    validation: AudioReviewValidation,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Validate or correct an audio review."""
    review = db.query(AudioReview).filter(AudioReview.id == review_id).first()

    if not review:
        raise HTTPException(status_code=404, detail="Revue non trouvee")

    if validation.status not in ("confirmed", "corrected"):
        raise HTTPException(
            status_code=400,
            detail="Statut invalide (confirmed ou corrected)",
        )

    review.review_status = validation.status
    review.reviewer_id = current_user.id
    review.reviewed_at = datetime.utcnow()
    review.reviewer_comment = validation.comment

    db.commit()

    return {
        "message": "Revue mise a jour",
        "review_id": review_id,
        "new_status": review.review_status,
        "reviewed_by": current_user.email,
    }
