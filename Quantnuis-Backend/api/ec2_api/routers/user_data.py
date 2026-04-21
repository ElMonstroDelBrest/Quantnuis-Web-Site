#!/usr/bin/env python3
"""
================================================================================
                    EC2 API - USER DATA ROUTER
================================================================================

User data endpoints: /stats, /history, /analysis-results

================================================================================
"""

from typing import List

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from pydantic import BaseModel

from config import get_settings
from database import get_db, User, CarDetection, NoisyCarAnalysis
from database.schemas import UserStats, HistoryEntry
from ..dependencies import get_current_user, get_optional_user

router = APIRouter(tags=["user-data"])
settings = get_settings()


# ==============================================================================
# SCHEMAS FOR ANALYSIS RESULTS
# ==============================================================================

class AnalysisResultCreate(BaseModel):
    """Schema for storing analysis results from Lambda."""
    filename: str
    car_detected: bool
    car_confidence: float
    car_probability: float
    is_noisy: bool | None = None
    noisy_confidence: float | None = None
    noisy_probability: float | None = None


# ==============================================================================
# ENDPOINTS
# ==============================================================================

@router.get("/stats", response_model=UserStats)
async def get_stats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get user statistics."""
    # Count detections
    detections = db.query(CarDetection).filter(
        CarDetection.user_id == current_user.id
    ).all()

    total = len(detections)

    # Count noisy vehicles
    noisy_count = db.query(NoisyCarAnalysis).filter(
        NoisyCarAnalysis.user_id == current_user.id,
        NoisyCarAnalysis.is_noisy == True
    ).count()

    # Last analysis
    last_detection = db.query(CarDetection).filter(
        CarDetection.user_id == current_user.id
    ).order_by(CarDetection.timestamp.desc()).first()

    return {
        "total_analyses": total,
        "noisy_detections": noisy_count,
        "last_analysis_date": last_detection.timestamp if last_detection else None
    }


@router.get("/history", response_model=List[HistoryEntry])
async def get_history(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    limit: int = 50
):
    """Get user's analysis history."""
    detections = db.query(CarDetection).filter(
        CarDetection.user_id == current_user.id
    ).order_by(CarDetection.timestamp.desc()).limit(limit).all()

    history = []
    for detection in detections:
        # Determine if noisy (car detected AND noisy)
        is_noisy = False
        confidence = detection.confidence

        if detection.car_detected and detection.noisy_analysis:
            is_noisy = detection.noisy_analysis.is_noisy
            confidence = detection.noisy_analysis.confidence

        entry = {
            "id": detection.id,
            "filename": detection.filename,
            "timestamp": detection.timestamp,
            "is_noisy": is_noisy,
            "confidence": confidence
        }

        history.append(entry)

    return history


@router.post("/analysis-results")
async def store_analysis_results(
    result: AnalysisResultCreate,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Store analysis results from Lambda.

    This endpoint is called by the Lambda API after performing audio analysis.
    It stores the results in the PostgreSQL database.
    """
    # Get user from token (optional - allows anonymous storage with user tracking)
    user = get_optional_user(request, db)

    if not user:
        raise HTTPException(status_code=401, detail="Authentication required to store results")

    # Create CarDetection entry
    car_detection = CarDetection(
        filename=result.filename,
        car_detected=result.car_detected,
        confidence=result.car_confidence,
        probability=result.car_probability,
        user_id=user.id
    )
    db.add(car_detection)
    db.flush()  # Get the ID

    # If car detected, create NoisyCarAnalysis
    if result.car_detected and result.is_noisy is not None:
        noisy_analysis = NoisyCarAnalysis(
            is_noisy=result.is_noisy,
            confidence=result.noisy_confidence or 0,
            probability=result.noisy_probability or 0,
            car_detection_id=car_detection.id,
            user_id=user.id
        )
        db.add(noisy_analysis)

    db.commit()

    return {
        "message": "Analysis results stored successfully",
        "detection_id": car_detection.id
    }
