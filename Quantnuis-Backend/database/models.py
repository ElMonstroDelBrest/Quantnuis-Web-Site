#!/usr/bin/env python3
"""
================================================================================
                    MODÈLES ORM
================================================================================

Définition des modèles SQLAlchemy pour la base de données.

Tables :
    - User : Utilisateurs de l'application
    - CarDetection : Résultats du modèle 1 (détection voiture)
    - NoisyCarAnalysis : Résultats du modèle 2 (voiture bruyante)

================================================================================
"""

import datetime
from sqlalchemy import (
    Boolean, Column, ForeignKey, Integer, String, 
    Float, DateTime, Text, Enum
)
from sqlalchemy.orm import relationship
import enum

from .connection import Base


# ==============================================================================
# ÉNUMÉRATIONS
# ==============================================================================

class AnalysisStatus(str, enum.Enum):
    """Statut d'une analyse."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    ERROR = "error"


# ==============================================================================
# MODÈLE USER
# ==============================================================================

class User(Base):
    """
    Utilisateur de l'application.
    
    Attributs:
        id: Identifiant unique
        email: Email (unique)
        hashed_password: Mot de passe hashé
        is_active: Compte actif ou non
        created_at: Date de création
        
    Relations:
        car_detections: Détections de voiture de cet utilisateur
        noisy_analyses: Analyses de voiture bruyante de cet utilisateur
    """
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    
    # Relations
    car_detections = relationship("CarDetection", back_populates="owner")
    noisy_analyses = relationship("NoisyCarAnalysis", back_populates="owner")


# ==============================================================================
# MODÈLE CAR DETECTION (Résultats modèle 1)
# ==============================================================================

class CarDetection(Base):
    """
    Résultat d'une détection de voiture (modèle 1).
    
    Stocke les résultats de l'analyse par le premier modèle.
    Sert de base de données intermédiaire pour le modèle 2.
    
    Attributs:
        id: Identifiant unique
        filename: Nom du fichier audio original
        car_detected: Voiture détectée ou non
        confidence: Confiance de la détection (0-100)
        probability: Probabilité brute (0-1)
        timestamp: Date/heure de l'analyse
        status: Statut de l'analyse
        user_id: Utilisateur ayant fait l'analyse
        
    Relations:
        owner: Utilisateur propriétaire
        noisy_analysis: Analyse de bruit associée (si voiture détectée)
    """
    __tablename__ = "car_detections"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String, nullable=False)
    car_detected = Column(Boolean, nullable=False)
    confidence = Column(Float, nullable=False)
    probability = Column(Float, nullable=False)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow, index=True)
    status = Column(String, default=AnalysisStatus.COMPLETED)
    
    # Métadonnées audio (optionnel)
    audio_duration = Column(Float, nullable=True)  # Durée en secondes
    
    # Clé étrangère
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    
    # Relations
    owner = relationship("User", back_populates="car_detections")
    noisy_analysis = relationship(
        "NoisyCarAnalysis", 
        back_populates="car_detection",
        uselist=False  # Relation 1-to-1
    )


# ==============================================================================
# MODÈLE NOISY CAR ANALYSIS (Résultats modèle 2)
# ==============================================================================

class NoisyCarAnalysis(Base):
    """
    Résultat d'une analyse de voiture bruyante (modèle 2).
    
    Créé UNIQUEMENT si une voiture a été détectée par le modèle 1.
    
    Attributs:
        id: Identifiant unique
        is_noisy: Voiture bruyante ou non
        confidence: Confiance de l'analyse (0-100)
        probability: Probabilité brute (0-1)
        estimated_db: Estimation des décibels (optionnel)
        timestamp: Date/heure de l'analyse
        
        car_detection_id: Référence à la détection de voiture
        user_id: Utilisateur ayant fait l'analyse
        
    Relations:
        car_detection: Détection de voiture associée
        owner: Utilisateur propriétaire
    """
    __tablename__ = "noisy_car_analyses"

    id = Column(Integer, primary_key=True, index=True)
    is_noisy = Column(Boolean, nullable=False)
    confidence = Column(Float, nullable=False)
    probability = Column(Float, nullable=False)
    estimated_db = Column(Integer, nullable=True)  # Estimation décibels
    timestamp = Column(DateTime, default=datetime.datetime.utcnow, index=True)
    
    # Clés étrangères
    car_detection_id = Column(
        Integer, 
        ForeignKey("car_detections.id"), 
        nullable=False,
        unique=True  # 1-to-1 avec CarDetection
    )
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    
    # Relations
    car_detection = relationship("CarDetection", back_populates="noisy_analysis")
    owner = relationship("User", back_populates="noisy_analyses")


# ==============================================================================
# FONCTION D'INITIALISATION
# ==============================================================================

def create_all_tables(engine):
    """Crée toutes les tables dans la base de données."""
    Base.metadata.create_all(bind=engine)
