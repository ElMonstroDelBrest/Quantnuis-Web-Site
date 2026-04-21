#!/usr/bin/env python3
"""
================================================================================
                    LAMBDA API - PREDICT ROUTER
================================================================================

Prediction endpoints: /predict, /predict/detailed

Stateless audio analysis using TensorFlow models.
No database operations - results can be stored via EC2 API.

================================================================================
"""

import os
import shutil
import tempfile
from pathlib import Path

from fastapi import APIRouter, UploadFile, File, HTTPException, Request
from jose import jwt, JWTError

from config import get_settings
from pipeline import Pipeline

router = APIRouter(tags=["prediction"])
settings = get_settings()

ALLOWED_EXTENSIONS = {".wav", ".mp3", ".ogg", ".flac", ".m4a"}
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 MB

# Pipeline global — load_models() appelé depuis main.py après download S3
pipeline = Pipeline()


def _validate_audio_file(file: UploadFile):
    """Valide le type et l'extension d'un fichier audio. Lève HTTPException si invalide."""
    if file.content_type and not file.content_type.startswith("audio/") \
            and file.content_type != "application/octet-stream":
        raise HTTPException(status_code=400, detail="Le fichier doit etre un fichier audio")
    suffix = Path(file.filename).suffix.lower() if file.filename else ""
    if suffix not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Format non supporte. Extensions: {', '.join(ALLOWED_EXTENSIONS)}"
        )
    return suffix


def get_user_email_from_token(request: Request) -> str | None:
    """Extract user email from JWT token if present."""
    auth_header = request.headers.get('Authorization')

    if not auth_header or not auth_header.startswith("Bearer "):
        return None

    token = auth_header.split(" ")[1]

    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload.get("sub")
    except JWTError:
        return None


@router.post("/predict")
async def predict_audio(
    request: Request,
    file: UploadFile = File(...)
):
    """
    Analyze an audio file with the full pipeline.

    The pipeline:
    1. Detects if a vehicle is present
    2. If yes, analyzes if it's noisy

    Parameters:
        file: Audio file (wav, mp3, etc.)

    Returns:
        Simplified format for frontend compatibility:
        - hasNoisyVehicle: bool
        - carDetected: bool
        - confidence: float (0-1)
        - message: str
    """
    # Get user email if authenticated (for logging purposes)
    user_email = get_user_email_from_token(request)

    suffix = _validate_audio_file(file)

    # Save file temporarily
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix, dir='/tmp') as temp_file:
        temp_path = temp_file.name
        try:
            shutil.copyfileobj(file.file, temp_file)
        finally:
            file.file.close()

    # Validate file size after write
    file_size = os.path.getsize(temp_path)
    if file_size > MAX_FILE_SIZE:
        os.unlink(temp_path)
        raise HTTPException(status_code=413, detail=f"Fichier trop volumineux. Taille maximum: {MAX_FILE_SIZE // (1024*1024)} MB")
    if file_size == 0:
        os.unlink(temp_path)
        raise HTTPException(status_code=400, detail="Fichier vide")

    try:
        # Execute pipeline
        result = pipeline.analyze(temp_path, verbose=False)

        # Return simplified format
        response = result.to_simplified()

        # Add filename for potential storage via EC2 API
        response["filename"] = file.filename or "unknown"

        # Add full result data for EC2 storage endpoint
        response["_full_result"] = {
            "car_detected": result.car_detected,
            "car_confidence": result.car_confidence,
            "car_probability": result.car_probability,
            "is_noisy": result.is_noisy,
            "noisy_confidence": result.noisy_confidence,
            "noisy_probability": result.noisy_probability,
        }

        return response

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        # Cleanup temporary file
        if os.path.exists(temp_path):
            os.unlink(temp_path)


@router.post("/predict/detailed")
async def predict_audio_detailed(
    request: Request,
    file: UploadFile = File(...)
):
    """
    Analyze an audio file and return detailed results.

    Returns complete results from both models.
    """
    suffix = _validate_audio_file(file)

    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix, dir='/tmp') as temp_file:
        temp_path = temp_file.name
        try:
            shutil.copyfileobj(file.file, temp_file)
        finally:
            file.file.close()

    file_size = os.path.getsize(temp_path)
    if file_size > MAX_FILE_SIZE:
        os.unlink(temp_path)
        raise HTTPException(status_code=413, detail=f"Fichier trop volumineux. Taille maximum: {MAX_FILE_SIZE // (1024*1024)} MB")
    if file_size == 0:
        os.unlink(temp_path)
        raise HTTPException(status_code=400, detail="Fichier vide")

    try:
        result = pipeline.analyze(temp_path, verbose=False)

        response = result.to_dict()
        response["filename"] = file.filename or "unknown"

        return response

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        if os.path.exists(temp_path):
            os.unlink(temp_path)
