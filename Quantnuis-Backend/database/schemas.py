#!/usr/bin/env python3
"""
================================================================================
                    SCHÉMAS PYDANTIC
================================================================================

Schémas de validation pour l'API FastAPI.

================================================================================
"""

from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime


# ==============================================================================
# SCHÉMAS USER
# ==============================================================================

class UserBase(BaseModel):
    """Base commune pour les schémas User."""
    email: EmailStr


class UserCreate(UserBase):
    """Schéma pour la création d'un utilisateur."""
    password: str


class User(UserBase):
    """Schéma de réponse pour un utilisateur."""
    id: int
    is_active: bool
    is_admin: bool = False
    created_at: datetime

    class Config:
        from_attributes = True


# ==============================================================================
# SCHÉMAS TOKEN (Auth)
# ==============================================================================

class Token(BaseModel):
    """Schéma de réponse pour un token JWT."""
    access_token: str
    token_type: str


class TokenData(BaseModel):
    """Données contenues dans un token."""
    email: Optional[str] = None


# ==============================================================================
# SCHÉMAS CAR DETECTION
# ==============================================================================

class CarDetectionBase(BaseModel):
    """Base commune pour les détections de voiture."""
    filename: str
    car_detected: bool
    confidence: float
    probability: float


class CarDetectionCreate(CarDetectionBase):
    """Schéma pour créer une détection."""
    pass


class CarDetection(CarDetectionBase):
    """Schéma de réponse pour une détection."""
    id: int
    timestamp: datetime
    status: str
    user_id: Optional[int] = None
    
    class Config:
        from_attributes = True


# ==============================================================================
# SCHÉMAS NOISY CAR ANALYSIS
# ==============================================================================

class NoisyCarAnalysisBase(BaseModel):
    """Base commune pour les analyses de bruit."""
    is_noisy: bool
    confidence: float
    probability: float


class NoisyCarAnalysisCreate(NoisyCarAnalysisBase):
    """Schéma pour créer une analyse de bruit."""
    car_detection_id: int


class NoisyCarAnalysis(NoisyCarAnalysisBase):
    """Schéma de réponse pour une analyse de bruit."""
    id: int
    timestamp: datetime
    car_detection_id: int
    user_id: Optional[int] = None
    
    class Config:
        from_attributes = True


# ==============================================================================
# SCHÉMAS PIPELINE COMPLET
# ==============================================================================

class PipelineResult(BaseModel):
    """
    Résultat complet du pipeline (2 modèles).
    
    Utilisé pour la réponse de l'endpoint /predict.
    """
    # Résultat modèle 1 : Détection voiture
    car_detected: bool
    car_confidence: float
    car_probability: float
    
    # Résultat modèle 2 : Voiture bruyante (si voiture détectée)
    is_noisy: Optional[bool] = None
    noisy_confidence: Optional[float] = None
    noisy_probability: Optional[float] = None

    # Résumé
    message: str
    
    class Config:
        from_attributes = True


class PipelineResultSimplified(BaseModel):
    """
    Version simplifiée du résultat pour compatibilité avec l'ancien format.
    """
    hasNoisyVehicle: bool
    carDetected: bool
    confidence: float
    message: str


# ==============================================================================
# SCHÉMAS STATISTIQUES
# ==============================================================================

class UserStats(BaseModel):
    """Statistiques d'un utilisateur."""
    total_analyses: int
    noisy_detections: int  # Compatibilité avec le frontend existant
    last_analysis_date: Optional[datetime] = None


class GlobalStats(BaseModel):
    """Statistiques globales du système."""
    total_users: int
    total_analyses: int
    total_cars_detected: int
    total_noisy_vehicles: int
    detection_rate: float  # Pourcentage de voitures détectées
    noisy_rate: float  # Pourcentage de voitures bruyantes


# ==============================================================================
# SCHÉMAS HISTORIQUE
# ==============================================================================

class HistoryEntry(BaseModel):
    """
    Entrée dans l'historique d'un utilisateur.

    Format compatible avec le frontend existant.
    """
    id: int
    filename: str
    timestamp: datetime
    is_noisy: bool  # Résultat final (voiture bruyante ou non)
    confidence: float  # Confiance en pourcentage (0-100)

    class Config:
        from_attributes = True


# ==============================================================================
# SCHÉMAS ANNOTATION REQUEST
# ==============================================================================

class AnnotationData(BaseModel):
    """Données d'une annotation individuelle."""
    start: str  # Format HH:MM:SS
    end: str
    label: str
    reliability: int = 3
    note: Optional[str] = None


class AnnotationRequestCreate(BaseModel):
    """Schéma pour soumettre une demande d'annotation."""
    model_type: str  # "car" ou "noisy_car"
    annotations: List[AnnotationData]


class AnnotationRequestResponse(BaseModel):
    """Schéma de réponse pour une demande d'annotation."""
    id: int
    filename: str
    model_type: str
    status: str
    annotation_count: int
    total_duration: Optional[float] = None
    created_at: datetime
    reviewed_at: Optional[datetime] = None
    admin_note: Optional[str] = None
    submitted_by_email: Optional[str] = None
    reviewed_by_email: Optional[str] = None

    class Config:
        from_attributes = True


class AnnotationRequestReview(BaseModel):
    """Schéma pour l'action d'un admin sur une demande."""
    action: str  # "approve" ou "reject"
    note: Optional[str] = None


class AnnotationRequestStats(BaseModel):
    """Statistiques des demandes d'annotations."""
    total_pending: int
    total_approved: int
    total_rejected: int
    total_annotations_integrated: int


# ==============================================================================
# SCHÉMAS AUDIO REVIEW
# ==============================================================================

class AudioReviewResponse(BaseModel):
    """Schéma de réponse pour une revue audio IA."""
    id: int
    s3_key: str
    car_detected: bool
    car_confidence: float
    car_probability: float
    is_noisy: Optional[bool] = None
    noisy_confidence: Optional[float] = None
    noisy_probability: Optional[float] = None
    review_status: str
    reviewer_comment: Optional[str] = None
    analyzed_at: datetime
    reviewed_at: Optional[datetime] = None
    audio_url: Optional[str] = None

    class Config:
        from_attributes = True


class AudioReviewListResponse(BaseModel):
    """Réponse paginée pour la liste des revues audio."""
    reviews: List[AudioReviewResponse]
    total: int
    page: int
    page_size: int


class AudioReviewValidation(BaseModel):
    """Schéma pour valider/corriger une revue audio."""
    status: str  # "confirmed" ou "corrected"
    comment: Optional[str] = None


class AudioReviewStats(BaseModel):
    """Statistiques des revues audio IA."""
    total: int
    pending: int
    confirmed: int
    corrected: int
    accuracy_rate: Optional[float] = None
