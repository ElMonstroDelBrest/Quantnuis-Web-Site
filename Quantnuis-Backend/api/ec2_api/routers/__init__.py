# EC2 API Routers
from .auth import router as auth_router
from .user_data import router as user_data_router
from .annotations import router as annotations_router
from .admin import router as admin_router
from .s3_audio import router as s3_audio_router
from .audio_reviews import router as audio_reviews_router

__all__ = [
    "auth_router",
    "user_data_router",
    "annotations_router",
    "admin_router",
    "s3_audio_router",
    "audio_reviews_router",
]
