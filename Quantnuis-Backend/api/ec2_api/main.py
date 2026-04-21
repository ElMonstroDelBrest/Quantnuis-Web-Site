#!/usr/bin/env python3
"""
================================================================================
                    EC2 API - MAIN ENTRY POINT
================================================================================

Stateful API for authentication, user data, and annotations.
Runs on EC2 with PostgreSQL database.

Endpoints:
    - POST /register      : User registration
    - POST /token         : Authentication (JWT)
    - GET  /users/me      : User information
    - GET  /stats         : User statistics
    - GET  /history       : Analysis history
    - POST /analysis-results : Store results from Lambda
    - POST /annotation-requests : Submit annotation request
    - GET  /annotation-requests/my : User's annotation requests
    - GET  /admin/*       : Admin endpoints
    - GET  /health        : Health check

Usage:
    uvicorn api.ec2_api.main:app --reload --host 0.0.0.0 --port 8000

================================================================================
"""

import os

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from config import get_settings
from database import engine
from database.models import create_all_tables

from .routers import (
    auth_router, user_data_router, annotations_router,
    admin_router, s3_audio_router, audio_reviews_router,
)


# ==============================================================================
# CONFIGURATION
# ==============================================================================

settings = get_settings()

# Create database tables
create_all_tables(engine)


# ==============================================================================
# APPLICATION FASTAPI
# ==============================================================================

app = FastAPI(
    title="Quantnuis EC2 API",
    description="Stateful API for authentication, user data, and annotations",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Rate limiting
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


# ==============================================================================
# MIDDLEWARE CORS
# ==============================================================================

# Get CORS origins from environment — default to known production domains
_default_origins = (
    "https://www.quantnuis.fr,"
    "https://quantnuis.fr,"
    "http://localhost:4200"
)
cors_origins_str = os.environ.get("CORS_ORIGINS", _default_origins)
cors_origins = [origin.strip() for origin in cors_origins_str.split(",") if origin.strip()]

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

app.include_router(auth_router)
app.include_router(user_data_router)
app.include_router(annotations_router)
app.include_router(admin_router)
app.include_router(s3_audio_router)
app.include_router(audio_reviews_router)


# ==============================================================================
# HEALTH CHECK
# ==============================================================================

@app.get("/health")
async def health_check():
    """Check that the API is running."""
    from sqlalchemy import text
    # Check database connection
    db_status = "unknown"
    db_type = "unknown"

    try:
        from database import SessionLocal
        db = SessionLocal()
        db.execute(text("SELECT 1"))
        db.close()
        db_status = "connected"

        # Detect database type from URL
        if "postgresql" in settings.DATABASE_URL:
            db_type = "postgresql"
        elif "sqlite" in settings.DATABASE_URL:
            db_type = "sqlite"
    except Exception as e:
        db_status = f"error: {str(e)}"

    return {
        "status": "ok",
        "service": "ec2-api",
        "version": "2.0.0",
        "database": {
            "type": db_type,
            "status": db_status
        }
    }


# ==============================================================================
# LOCAL ENTRY POINT
# ==============================================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
