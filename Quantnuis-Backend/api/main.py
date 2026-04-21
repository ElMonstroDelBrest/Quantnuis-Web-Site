#!/usr/bin/env python3
"""
================================================================================
                    API COMBINEE - DEVELOPPEMENT LOCAL
================================================================================

Wrapper leger qui monte les routers EC2 (auth, users, admin) et Lambda
(predict) sur une seule app FastAPI. Utilise pour le dev local uniquement.

En production, ces API tournent separement :
  - EC2 : api.ec2_api.main (auth, users, admin, annotations, S3)
  - Lambda : api.lambda_api.main (predict IA)

Usage:
    uvicorn api.main:app --reload --host 0.0.0.0 --port 8000

================================================================================
"""

import os

# Caches pour Lambda/TensorFlow (avant les imports)
os.environ['NUMBA_CACHE_DIR'] = '/tmp'
os.environ['MPLCONFIGDIR'] = '/tmp'
os.environ['TRANSFORMERS_CACHE'] = '/tmp'
os.environ['XDG_CACHE_HOME'] = '/tmp'

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from mangum import Mangum

from config import get_settings

settings = get_settings()


# ==============================================================================
# S3 MODEL DOWNLOAD (Lambda cold start - MUST run before pipeline import)
# ==============================================================================

def _download_models_from_s3():
    """Download ML model artifacts from S3 to /tmp/ on Lambda cold start."""
    if not settings.IS_LAMBDA:
        return

    import boto3
    from botocore.exceptions import ClientError

    s3 = boto3.client('s3')
    bucket = settings.S3_MODELS_BUCKET

    artifacts = [
        # CarDetector — CRNN (prioritaire) + MLP (fallback)
        "car_detector/artifacts/crnn_car_detector.h5",
        "car_detector/artifacts/crnn_config.json",
        "car_detector/artifacts/model.h5",
        "car_detector/artifacts/scaler.pkl",
        "car_detector/artifacts/features.txt",
        # NoisyCarDetector — CNN + MLP fallback
        "noisy_car_detector/artifacts/cnn_noisy_car.h5",
        "noisy_car_detector/artifacts/cnn_config.json",
        "noisy_car_detector/artifacts/model.h5",
        "noisy_car_detector/artifacts/scaler.pkl",
        "noisy_car_detector/artifacts/features.txt",
    ]

    downloaded = 0
    for artifact in artifacts:
        s3_key = f"models/{artifact}"
        local_path = f"/tmp/models/{artifact}"

        if os.path.exists(local_path):
            continue

        os.makedirs(os.path.dirname(local_path), exist_ok=True)

        try:
            s3.download_file(bucket, s3_key, local_path)
            downloaded += 1
        except ClientError:
            print(f"[S3] Model artifact not found: {s3_key}")

    if downloaded > 0:
        print(f"[S3] Downloaded {downloaded} model artifact(s)")


_download_models_from_s3()


# ==============================================================================
# IMPORTS (after S3 download so models are available)
# ==============================================================================

from database import engine
from database.models import create_all_tables

# Routers EC2 (stateful)
from api.ec2_api.routers import (
    auth_router, user_data_router, annotations_router,
    admin_router, s3_audio_router
)
# Router Lambda (stateless IA) - triggers Pipeline.load_models() at import time
from api.lambda_api.routers import predict_router


# ==============================================================================
# DATABASE INIT
# ==============================================================================

create_all_tables(engine)


# ==============================================================================
# APPLICATION FASTAPI
# ==============================================================================

app = FastAPI(
    title="Quantnuis API",
    description="API combinee (dev local). En production : EC2 + Lambda.",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

handler = Mangum(app, lifespan="off")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ==============================================================================
# ROUTERS
# ==============================================================================

# EC2 : authentification, donnees utilisateur, annotations, admin, S3 audio
app.include_router(auth_router)
app.include_router(user_data_router)
app.include_router(annotations_router)
app.include_router(admin_router)
app.include_router(s3_audio_router)

# Lambda : prediction IA
app.include_router(predict_router)


# ==============================================================================
# HEALTH CHECK
# ==============================================================================

@app.get("/health")
async def health_check():
    """Verification sante combinant les deux services."""
    from sqlalchemy import text
    from database import SessionLocal

    # Verifier la BDD
    db_status = "unknown"
    try:
        db = SessionLocal()
        db.execute(text("SELECT 1"))
        db.close()
        db_status = "connected"
    except Exception as e:
        db_status = f"error: {str(e)}"

    # Verifier les modeles (charges par le router predict)
    try:
        from api.lambda_api.routers.predict import pipeline
        models_status = {
            "car_detector": pipeline.car_detector.is_loaded,
            "noisy_car_detector": pipeline.noisy_car_detector.is_loaded
        }
    except Exception:
        models_status = {"car_detector": False, "noisy_car_detector": False}

    return {
        "status": "ok",
        "service": "combined-dev",
        "version": "2.0.0",
        "database": db_status,
        "models": models_status
    }


# ==============================================================================
# POINT D'ENTREE LOCAL
# ==============================================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
