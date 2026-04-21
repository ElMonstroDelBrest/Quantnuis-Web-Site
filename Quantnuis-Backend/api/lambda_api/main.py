#!/usr/bin/env python3
"""
================================================================================
                    LAMBDA API - MAIN ENTRY POINT
================================================================================

Stateless AI API for audio predictions.
Runs on AWS Lambda with TensorFlow models.

Endpoints:
    - POST /predict           : Analyze audio (simple response)
    - POST /predict/detailed  : Analyze audio (full response)
    - GET  /health            : Health check with model status

Usage local:
    uvicorn api.lambda_api.main:app --reload --host 0.0.0.0 --port 8001

AWS Lambda:
    The Mangum handler is exported automatically.

================================================================================
"""

import os

# Configure caches for AWS Lambda (MUST be done BEFORE imports)
os.environ['NUMBA_CACHE_DIR'] = '/tmp'
os.environ['MPLCONFIGDIR'] = '/tmp'
os.environ['TRANSFORMERS_CACHE'] = '/tmp'
os.environ['XDG_CACHE_HOME'] = '/tmp'

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from mangum import Mangum

from config import get_settings
from pipeline import Pipeline

from .routers import predict_router
from .routers.predict import pipeline as _pipeline


# ==============================================================================
# CONFIGURATION
# ==============================================================================

settings = get_settings()


# ==============================================================================
# APPLICATION FASTAPI
# ==============================================================================

app = FastAPI(
    title="Quantnuis AI Lambda",
    description="Stateless AI API for audio predictions",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Handler for AWS Lambda
handler = Mangum(app, lifespan="off")


# ==============================================================================
# MIDDLEWARE CORS
# ==============================================================================

# Get CORS origins from environment or use defaults
cors_origins_str = os.environ.get("CORS_ORIGINS", "*")
if cors_origins_str == "*":
    cors_origins = ["*"]
else:
    cors_origins = [origin.strip() for origin in cors_origins_str.split(",")]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ==============================================================================
# ROUTERS
# ==============================================================================

app.include_router(predict_router)


# ==============================================================================
# S3 MODEL DOWNLOAD (Lambda cold start)
# ==============================================================================

def _download_models_from_s3():
    """Download ML model artifacts from S3 to /tmp/ on Lambda cold start (parallel)."""
    if not settings.IS_LAMBDA:
        return

    import boto3
    from botocore.exceptions import ClientError
    from concurrent.futures import ThreadPoolExecutor, as_completed
    from shared.logger import print_info, print_success, print_warning, print_error

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

    # Filter to only missing artifacts (skip warm-start hits)
    to_download = []
    for artifact in artifacts:
        local_path = f"/tmp/models/{artifact}"
        if not os.path.exists(local_path):
            os.makedirs(os.path.dirname(local_path), exist_ok=True)
            to_download.append(artifact)

    if not to_download:
        return

    print_info(f"Downloading {len(to_download)} model artifact(s) from S3...")

    def _fetch(artifact):
        local_path = f"/tmp/models/{artifact}"
        try:
            s3.download_file(bucket, f"models/{artifact}", local_path)
            return artifact, None
        except ClientError as e:
            return artifact, str(e)

    errors = []
    with ThreadPoolExecutor(max_workers=4) as pool:
        futures = {pool.submit(_fetch, a): a for a in to_download}
        for future in as_completed(futures):
            artifact, err = future.result()
            if err:
                print_warning(f"  Missing S3 artifact: models/{artifact}")
                errors.append(artifact)

    downloaded = len(to_download) - len(errors)
    if downloaded > 0:
        print_success(f"Downloaded {downloaded} artifact(s) from S3")

    # Fail fast if critical model files are missing
    critical = {"car_detector/artifacts/crnn_car_detector.h5",
                "noisy_car_detector/artifacts/cnn_noisy_car.h5"}
    missing_critical = critical & set(errors)
    if missing_critical:
        msg = f"Critical model artifacts missing from S3: {missing_critical}"
        print_error(msg)
        raise RuntimeError(msg)


# 1. Download models from S3 (cold start)
_download_models_from_s3()
# 2. Load models into pipeline (après download, dans le bon ordre)
_pipeline.load_models()


# ==============================================================================
# HEALTH CHECK
# ==============================================================================

@app.get("/health")
async def health_check():
    """Check that the API is running and models are loaded."""
    return {
        "status": "ok",
        "service": "ai-lambda",
        "version": "2.0.0",
        "environment": "lambda" if settings.IS_LAMBDA else "local",
        "models": {
            "car_detector": _pipeline.car_detector.is_loaded,
            "noisy_car_detector": _pipeline.noisy_car_detector.is_loaded
        }
    }


# ==============================================================================
# LOCAL ENTRY POINT
# ==============================================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
