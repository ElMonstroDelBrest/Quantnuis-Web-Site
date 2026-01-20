#!/usr/bin/env python3
"""
================================================================================
                    CONFIGURATION CENTRALISÉE
================================================================================

Gestion de toute la configuration du projet via variables d'environnement
et valeurs par défaut. Compatible avec le développement local et AWS Lambda.

================================================================================
"""

import os
from functools import lru_cache
from pathlib import Path
from typing import Optional


class Settings:
    """
    Configuration centralisée du projet.
    
    Priorité : Variables d'environnement > Valeurs par défaut
    
    Usage:
        from config import get_settings
        settings = get_settings()
        print(settings.SAMPLE_RATE)
    """
    
    # ==========================================================================
    # DÉTECTION ENVIRONNEMENT
    # ==========================================================================
    
    @property
    def IS_LAMBDA(self) -> bool:
        """Détecte si on est sur AWS Lambda"""
        return bool(os.environ.get("AWS_LAMBDA_FUNCTION_NAME"))
    
    @property
    def IS_DEBUG(self) -> bool:
        """Mode debug actif"""
        return os.environ.get("DEBUG", "false").lower() == "true"
    
    # ==========================================================================
    # CHEMINS DE BASE
    # ==========================================================================
    
    @property
    def BASE_DIR(self) -> Path:
        """Racine du projet"""
        return Path(__file__).parent.parent
    
    @property
    def TMP_DIR(self) -> Path:
        """Répertoire temporaire (crucial pour Lambda)"""
        return Path("/tmp") if self.IS_LAMBDA else self.BASE_DIR / "tmp"
    
    @property
    def DATA_DIR(self) -> Path:
        """Répertoire des données"""
        return self.BASE_DIR / "data"
    
    # ==========================================================================
    # CONFIGURATION AUDIO
    # ==========================================================================
    
    SAMPLE_RATE: int = 22050
    """Fréquence d'échantillonnage standard (22.05 kHz)"""
    
    N_MFCC: int = 40
    """Nombre de coefficients MFCC à extraire"""
    
    # ==========================================================================
    # CONFIGURATION MODÈLE 1 : DÉTECTION VOITURE
    # ==========================================================================
    
    @property
    def CAR_DETECTOR_DIR(self) -> Path:
        """Dossier des artifacts du modèle détection voiture"""
        return self.BASE_DIR / "models" / "car_detector" / "artifacts"
    
    @property
    def CAR_MODEL_PATH(self) -> Path:
        """Chemin du modèle détection voiture"""
        return self.CAR_DETECTOR_DIR / "model.h5"
    
    @property
    def CAR_SCALER_PATH(self) -> Path:
        """Chemin du scaler détection voiture"""
        return self.CAR_DETECTOR_DIR / "scaler.pkl"
    
    @property
    def CAR_FEATURES_PATH(self) -> Path:
        """Chemin de la liste des features détection voiture"""
        return self.CAR_DETECTOR_DIR / "features.txt"
    
    CAR_DETECTION_THRESHOLD: float = 0.5
    """Seuil de détection de voiture (défaut: 0.5)"""
    
    # ==========================================================================
    # CONFIGURATION MODÈLE 2 : VOITURE BRUYANTE
    # ==========================================================================
    
    @property
    def NOISY_CAR_DETECTOR_DIR(self) -> Path:
        """Dossier des artifacts du modèle voiture bruyante"""
        return self.BASE_DIR / "models" / "noisy_car_detector" / "artifacts"
    
    @property
    def NOISY_CAR_MODEL_PATH(self) -> Path:
        """Chemin du modèle voiture bruyante"""
        return self.NOISY_CAR_DETECTOR_DIR / "model.h5"
    
    @property
    def NOISY_CAR_SCALER_PATH(self) -> Path:
        """Chemin du scaler voiture bruyante"""
        return self.NOISY_CAR_DETECTOR_DIR / "scaler.pkl"
    
    @property
    def NOISY_CAR_FEATURES_PATH(self) -> Path:
        """Chemin de la liste des features voiture bruyante"""
        return self.NOISY_CAR_DETECTOR_DIR / "features.txt"
    
    NOISY_THRESHOLD: float = 0.5
    """Seuil de détection voiture bruyante (défaut: 0.5)"""
    
    # ==========================================================================
    # CONFIGURATION BASE DE DONNÉES
    # ==========================================================================
    
    @property
    def DB_PATH(self) -> Path:
        """Chemin de la base SQLite"""
        # Priorité: variable d'environnement > Lambda > local
        env_path = os.environ.get("DATABASE_PATH")
        if env_path:
            return Path(env_path)
        if self.IS_LAMBDA:
            return Path("/tmp/quantnuis.db")
        return self.BASE_DIR / "quantnuis.db"
    
    @property
    def DATABASE_URL(self) -> str:
        """URL de connexion SQLAlchemy"""
        return f"sqlite:///{self.DB_PATH}"
    
    # ==========================================================================
    # CONFIGURATION S3
    # ==========================================================================
    
    S3_BUCKET_NAME: str = os.environ.get("DB_BUCKET_NAME", "quantnuis-db-bucket")
    """Nom du bucket S3 pour la persistance de la BDD"""
    
    # ==========================================================================
    # CONFIGURATION API / SÉCURITÉ
    # ==========================================================================
    
    SECRET_KEY: str = os.environ.get(
        "SECRET_KEY", 
        "dev_secret_key_a_changer_en_production_absolument"
    )
    """Clé secrète pour JWT (CHANGER EN PRODUCTION !)"""
    
    ALGORITHM: str = "HS256"
    """Algorithme de signature JWT"""
    
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(
        os.environ.get("ACCESS_TOKEN_EXPIRE_MINUTES", "30")
    )
    """Durée de validité du token (minutes)"""
    
    # ==========================================================================
    # CONFIGURATION ENTRAÎNEMENT
    # ==========================================================================
    
    TRAINING_EPOCHS: int = 60
    """Nombre d'epochs pour l'entraînement"""
    
    TRAINING_BATCH_SIZE: int = 16
    """Taille des batchs"""
    
    SMOTE_K_NEIGHBORS: int = 3
    """Nombre de voisins pour SMOTE (petit dataset = petit k)"""
    
    TEST_SIZE: float = 0.2
    """Proportion du dataset pour le test (20%)"""
    
    TOP_FEATURES_COUNT: int = 12
    """Nombre de features à sélectionner après analyse d'importance"""
    
    # ==========================================================================
    # CONFIGURATION CACHES (Lambda)
    # ==========================================================================
    
    def setup_lambda_caches(self):
        """Configure les répertoires de cache pour Lambda"""
        if self.IS_LAMBDA:
            os.environ['NUMBA_CACHE_DIR'] = '/tmp'
            os.environ['MPLCONFIGDIR'] = '/tmp'
            os.environ['TRANSFORMERS_CACHE'] = '/tmp'
            os.environ['XDG_CACHE_HOME'] = '/tmp'


@lru_cache()
def get_settings() -> Settings:
    """
    Retourne l'instance unique de Settings (singleton).
    
    Utilise @lru_cache pour éviter de recréer l'instance à chaque appel.
    
    Usage:
        from config import get_settings
        settings = get_settings()
    """
    settings = Settings()
    settings.setup_lambda_caches()
    return settings
