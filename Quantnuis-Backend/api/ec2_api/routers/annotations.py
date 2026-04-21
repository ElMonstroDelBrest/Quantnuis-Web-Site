#!/usr/bin/env python3
"""
================================================================================
                    EC2 API - ANNOTATIONS ROUTER
================================================================================

Annotation request endpoints: /annotation-requests, /annotation-requests/my

================================================================================
"""

import json
import shutil
from pathlib import Path
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, File, UploadFile
from sqlalchemy.orm import Session

from config import get_settings
from database import get_db, User, AnnotationRequest
from ..dependencies import get_current_user

router = APIRouter(prefix="/annotation-requests", tags=["annotations"])
settings = get_settings()

ALLOWED_EXTENSIONS = {".wav", ".mp3", ".ogg", ".flac", ".m4a"}


def get_annotation_requests_dir() -> Path:
    """Return the directory for annotation request audio files."""
    path = Path(settings.DATA_DIR) / "annotation_requests"
    path.mkdir(parents=True, exist_ok=True)
    return path


@router.post("")
async def submit_annotation_request(
    audio: UploadFile = File(...),
    annotations: UploadFile = File(...),
    model: str = "car",
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Submit an annotation request for admin approval.

    Parameters:
        audio: Source audio file
        annotations: CSV annotation file (Start,End,Label,Reliability,Note)
        model: Target model ("car" or "noisy_car")
    """
    # Validate model
    if model not in ["car", "noisy_car"]:
        raise HTTPException(status_code=400, detail="Modele invalide")

    # Validate audio file
    suffix = Path(audio.filename).suffix.lower() if audio.filename else ""
    if suffix not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail="Format audio non supporte")

    model_map = {"car": "car_detector", "noisy_car": "noisy_car_detector"}
    model_type = model_map[model]

    # Create unique folder for this request
    request_id = f"{current_user.id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    request_dir = get_annotation_requests_dir() / request_id
    request_dir.mkdir(parents=True, exist_ok=True)

    # Save audio file
    audio_path = request_dir / f"audio{suffix}"
    with open(audio_path, "wb") as f:
        shutil.copyfileobj(audio.file, f)

    # Read and parse annotations CSV
    annotations_content = annotations.file.read().decode('utf-8')
    lines = annotations_content.strip().split('\n')

    # Parse CSV (format: Start,End,Label,Reliability,Note)
    annotations_list = []
    total_duration = 0.0

    for line in lines[1:]:  # Skip header
        if not line.strip():
            continue
        parts = line.split(',')
        if len(parts) >= 4:
            start = parts[0].strip()
            end = parts[1].strip()
            label = parts[2].strip()
            reliability = int(parts[3].strip()) if parts[3].strip().isdigit() else 3
            note = parts[4].strip('"') if len(parts) > 4 else ""

            # Calculate duration
            def time_to_seconds(t):
                parts = t.split(':')
                if len(parts) == 3:
                    return int(parts[0])*3600 + int(parts[1])*60 + int(parts[2])
                elif len(parts) == 2:
                    return int(parts[0])*60 + int(parts[1])
                return 0

            duration = time_to_seconds(end) - time_to_seconds(start)
            total_duration += max(0, duration)

            annotations_list.append({
                "start": start,
                "end": end,
                "label": label,
                "reliability": reliability,
                "note": note
            })

    # Create DB entry
    annotation_request = AnnotationRequest(
        filename=audio.filename,
        audio_path=str(audio_path),
        annotations_data=json.dumps(annotations_list),
        model_type=model_type,
        annotation_count=len(annotations_list),
        total_duration=total_duration,
        user_id=current_user.id
    )

    db.add(annotation_request)
    db.commit()
    db.refresh(annotation_request)

    return {
        "message": "Demande soumise avec succes",
        "request_id": annotation_request.id,
        "status": "pending",
        "annotation_count": len(annotations_list),
        "awaiting_admin_approval": True
    }


@router.get("/my")
async def get_my_annotation_requests(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get the current user's annotation requests."""
    requests = db.query(AnnotationRequest).filter(
        AnnotationRequest.user_id == current_user.id
    ).order_by(AnnotationRequest.created_at.desc()).all()

    return [
        {
            "id": r.id,
            "filename": r.filename,
            "model_type": r.model_type,
            "status": r.status,
            "annotation_count": r.annotation_count,
            "total_duration": r.total_duration,
            "created_at": r.created_at,
            "reviewed_at": r.reviewed_at,
            "admin_note": r.admin_note
        }
        for r in requests
    ]
