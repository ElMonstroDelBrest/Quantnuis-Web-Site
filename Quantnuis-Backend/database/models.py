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


class AnnotationRequestStatus(str, enum.Enum):
    """Statut d'une demande d'annotation."""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class ReviewStatus(str, enum.Enum):
    """Statut de la revue humaine d'une prédiction IA."""
    PENDING = "pending"
    CONFIRMED = "confirmed"
    CORRECTED = "corrected"


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
        is_admin: Droits administrateur
        created_at: Date de création

    Relations:
        car_detections: Détections de voiture de cet utilisateur
        noisy_analyses: Analyses de voiture bruyante de cet utilisateur
        annotation_requests: Demandes d'annotation soumises par cet utilisateur
    """
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    is_admin = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    # Relations
    car_detections = relationship("CarDetection", back_populates="owner")
    noisy_analyses = relationship("NoisyCarAnalysis", back_populates="owner")
    annotation_requests = relationship("AnnotationRequest", back_populates="submitted_by", foreign_keys="AnnotationRequest.user_id")


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
# MODÈLE ANNOTATION REQUEST (Demandes d'annotation)
# ==============================================================================

class AnnotationRequest(Base):
    """
    Demande d'annotation soumise par un utilisateur.

    Les annotations doivent être approuvées par un admin avant d'être
    intégrées au dataset d'entraînement.

    Attributs:
        id: Identifiant unique
        filename: Nom du fichier audio original
        audio_path: Chemin vers le fichier audio stocké
        annotations_data: Données CSV des annotations (JSON)
        model_type: Type de modèle cible (car_detector ou noisy_car_detector)
        status: Statut de la demande (pending, approved, rejected)
        created_at: Date de soumission
        reviewed_at: Date de révision par l'admin
        admin_note: Note de l'admin (optionnel)

        user_id: Utilisateur ayant soumis la demande
        reviewed_by_id: Admin ayant traité la demande

    Relations:
        submitted_by: Utilisateur soumettant
        reviewed_by: Admin ayant traité
    """
    __tablename__ = "annotation_requests"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String, nullable=False)
    audio_path = Column(String, nullable=False)  # Chemin vers le fichier stocké
    annotations_data = Column(Text, nullable=False)  # JSON avec les annotations
    model_type = Column(String, nullable=False)  # "car_detector" ou "noisy_car_detector"
    status = Column(String, default=AnnotationRequestStatus.PENDING, index=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow, index=True)
    reviewed_at = Column(DateTime, nullable=True)
    admin_note = Column(Text, nullable=True)

    # Statistiques
    annotation_count = Column(Integer, default=0)
    total_duration = Column(Float, nullable=True)  # Durée totale annotée en secondes

    # Clés étrangères
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    reviewed_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    # Relations
    submitted_by = relationship("User", back_populates="annotation_requests", foreign_keys=[user_id])
    reviewed_by = relationship("User", foreign_keys=[reviewed_by_id])


# ==============================================================================
# MODÈLE AUDIO REVIEW (Revue IA des audios S3)
# ==============================================================================

class AudioReview(Base):
    """
    Résultat de l'analyse IA d'un fichier audio S3, en attente de validation humaine.

    Créé automatiquement lors du scan S3. Les utilisateurs valident ou corrigent
    la prédiction IA depuis le Dashboard.

    Attributs:
        s3_key: Clé S3 du fichier audio (unique, sert d'idempotence)
        car_detected, car_confidence, car_probability: Résultat modèle 1
        is_noisy, noisy_confidence, noisy_probability, estimated_db: Résultat modèle 2
        review_status: pending/confirmed/corrected
        reviewer_id: Utilisateur ayant validé
        reviewed_at: Date de validation
        reviewer_comment: Commentaire du validateur
        analyzed_at: Date de l'analyse IA
    """
    __tablename__ = "audio_reviews"

    id = Column(Integer, primary_key=True, index=True)
    s3_key = Column(String, unique=True, index=True, nullable=False)

    # Prédiction IA — Modèle 1 (détection voiture)
    car_detected = Column(Boolean, nullable=False)
    car_confidence = Column(Float, nullable=False)
    car_probability = Column(Float, nullable=False)

    # Prédiction IA — Modèle 2 (voiture bruyante, si voiture détectée)
    is_noisy = Column(Boolean, nullable=True)
    noisy_confidence = Column(Float, nullable=True)
    noisy_probability = Column(Float, nullable=True)
    estimated_db = Column(Integer, nullable=True)

    # Validation humaine
    review_status = Column(String, default=ReviewStatus.PENDING, index=True)
    reviewer_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    reviewed_at = Column(DateTime, nullable=True)
    reviewer_comment = Column(Text, nullable=True)

    # Timestamps
    analyzed_at = Column(DateTime, default=datetime.datetime.utcnow, index=True)

    # Relations
    reviewer = relationship("User", foreign_keys=[reviewer_id])


# ==============================================================================
# FONCTION D'INITIALISATION
# ==============================================================================

def create_all_tables(engine):
    """Crée toutes les tables dans la base de données."""
    Base.metadata.create_all(bind=engine)
