#!/usr/bin/env python3
"""
================================================================================
                    EC2 API - S3 AUDIO ROUTER
================================================================================

Endpoints pour la gestion des fichiers audio sur S3:
- GET /s3-audio/files         : Liste les fichiers audio disponibles
- GET /s3-audio/presigned-url : Genere une URL presignee pour telecharger un fichier
- GET /s3-audio/file-exists   : Verifie si un fichier existe

================================================================================
"""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from database import User, s3_audio_manager
from ..dependencies import get_current_user


router = APIRouter(prefix="/s3-audio", tags=["s3-audio"])


# ==============================================================================
# SCHEMAS
# ==============================================================================

class S3AudioFileResponse(BaseModel):
    """Schema pour un fichier audio S3."""
    key: str
    filename: str
    size: int
    size_formatted: str
    last_modified: Optional[str]


class S3AudioListResponse(BaseModel):
    """Schema pour la liste des fichiers audio."""
    files: List[S3AudioFileResponse]
    count: int
    bucket: str


class S3PresignedUrlResponse(BaseModel):
    """Schema pour une URL presignee."""
    url: str
    key: str
    expires_in: int


class S3FileExistsResponse(BaseModel):
    """Schema pour la verification d'existence."""
    exists: bool
    key: str


# ==============================================================================
# ENDPOINTS
# ==============================================================================

@router.get("/files", response_model=S3AudioListResponse)
async def list_audio_files(
    prefix: str = Query("", description="Prefixe (dossier) pour filtrer les fichiers"),
    max_files: int = Query(100, ge=1, le=500, description="Nombre maximum de fichiers"),
    current_user: User = Depends(get_current_user)
):
    """
    Liste les fichiers audio disponibles dans le bucket S3.

    Retourne les fichiers audio (.wav, .mp3, .ogg, .flac, .m4a)
    tries par date de modification (plus recent en premier).
    """
    try:
        files = s3_audio_manager.list_audio_files(prefix=prefix, max_files=max_files)

        return S3AudioListResponse(
            files=[
                S3AudioFileResponse(
                    key=f.key,
                    filename=f.filename,
                    size=f.size,
                    size_formatted=f.size_formatted,
                    last_modified=f.last_modified.isoformat() if f.last_modified else None
                )
                for f in files
            ],
            count=len(files),
            bucket=s3_audio_manager.bucket_name
        )

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/presigned-url", response_model=S3PresignedUrlResponse)
async def get_presigned_url(
    key: str = Query(..., description="Cle (chemin) du fichier dans S3"),
    expiration: int = Query(None, ge=60, le=43200, description="Duree de validite en secondes (1min-12h)"),
    current_user: User = Depends(get_current_user)
):
    """
    Genere une URL presignee pour telecharger un fichier audio.

    L'URL est valide pour la duree specifiee (defaut: 1 heure).
    """
    try:
        url = s3_audio_manager.get_presigned_url(key=key, expiration=expiration)

        return S3PresignedUrlResponse(
            url=url,
            key=key,
            expires_in=expiration or s3_audio_manager.client._client_config.signature_version and 3600
        )

    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/file-exists", response_model=S3FileExistsResponse)
async def check_file_exists(
    key: str = Query(..., description="Cle (chemin) du fichier dans S3"),
    current_user: User = Depends(get_current_user)
):
    """
    Verifie si un fichier existe dans le bucket S3.
    """
    try:
        exists = s3_audio_manager.file_exists(key=key)

        return S3FileExistsResponse(
            exists=exists,
            key=key
        )

    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))
