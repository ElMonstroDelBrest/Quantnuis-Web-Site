#!/usr/bin/env python3
"""
================================================================================
                    CONFIGURATION - VOITURE BRUYANTE
================================================================================

Configuration spécifique au modèle de détection de voiture bruyante.

Ce modèle ne traite QUE les audio où une voiture a déjà été détectée
par le premier modèle (car_detector).

Labels :
    - 0 : Voiture normale
    - 1 : Voiture bruyante

================================================================================
"""

from pathlib import Path
from config import get_settings

settings = get_settings()


# ==============================================================================
# CHEMINS DES FICHIERS
# ==============================================================================

ARTIFACTS_DIR = settings.NOISY_CAR_DETECTOR_DIR
"""Dossier contenant les artifacts du modèle"""

MODEL_PATH = settings.NOISY_CAR_MODEL_PATH
"""Chemin du modèle MLP .h5 (ancien)"""

SCALER_PATH = settings.NOISY_CAR_SCALER_PATH
"""Chemin du scaler .pkl (ancien MLP)"""

FEATURES_PATH = settings.NOISY_CAR_FEATURES_PATH
"""Chemin de la liste des features (ancien MLP)"""

# ==============================================================================
# CNN SUR MEL-SPECTROGRAMMES (nouveau modèle)
# ==============================================================================

CNN_MODEL_PATH = ARTIFACTS_DIR / "cnn_noisy_car.h5"
"""Chemin du modèle CNN .h5"""

CNN_CONFIG_PATH = ARTIFACTS_DIR / "cnn_config.json"
"""Chemin de la config CNN (normalisation, paramètres spectrogramme)"""


# ==============================================================================
# DONNÉES D'ENTRAÎNEMENT
# ==============================================================================

DATA_DIR = settings.DATA_DIR / "noisy_car_detector"
"""Dossier des données pour ce modèle"""

# Slices partagés OU spécifiques au modèle
SHARED_SLICES_DIR = settings.DATA_DIR / "slices"
"""Dossier commun des slices (si partagé entre modèles)"""

SLICES_DIR = SHARED_SLICES_DIR if SHARED_SLICES_DIR.exists() else DATA_DIR / "slices"
"""Dossier des slices audio (commun ou spécifique)"""

ANNOTATION_CSV = DATA_DIR / "annotation.csv"
"""Fichier d'annotations (nfile, label: 0=normal, 1=bruyant)"""

FEATURES_CSV = DATA_DIR / "features.csv"
"""Fichier des features extraites"""


# ==============================================================================
# PARAMÈTRES DU MODÈLE
# ==============================================================================

DETECTION_THRESHOLD = settings.NOISY_THRESHOLD
"""Seuil de détection (probabilité > seuil = voiture bruyante)"""

POSITIVE_LABEL = "BRUYANT"
"""Label pour la classe positive (voiture bruyante)"""

NEGATIVE_LABEL = "NORMAL"
"""Label pour la classe négative (voiture normale)"""


# ==============================================================================
# TOP FEATURES (à mettre à jour après analyse)
# ==============================================================================

DEFAULT_TOP_FEATURES = [
    'mfcc_39_mean', 'mfcc_11_std', 'mfcc_37_mean', 'mfcc_21_mean',
    'mfcc_24_std', 'spectral_bandwidth_mean', 'mfcc_31_std', 'mfcc_33_mean',
    'mfcc_17_mean', 'mfcc_6_mean', 'mfcc_12_std', 'chroma_7_mean'
]
"""Features par défaut si pas de fichier d'importance disponible"""
