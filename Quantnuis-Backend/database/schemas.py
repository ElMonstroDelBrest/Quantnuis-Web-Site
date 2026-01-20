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
    estimated_db: Optional[int] = None


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
    estimated_db: Optional[int] = None
    
    # Résumé
    message: str
    
    class Config:
        from_attributes = True


class PipelineResultSimplified(BaseModel):
    """
    Version simplifiée du résultat pour compatibilité avec l'ancien format.
    """
    hasNoisyVehicle: bool
    confidence: float
    maxDecibels: int
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
