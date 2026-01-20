#!/usr/bin/env python3
"""
================================================================================
                    CONFIGURATION - DÉTECTION VOITURE
================================================================================

Configuration spécifique au modèle de détection de voiture.

Labels :
    - 0 : Pas de voiture détectée
    - 1 : Voiture détectée

================================================================================
"""

from pathlib import Path
from config import get_settings

settings = get_settings()


# ==============================================================================
# CHEMINS DES FICHIERS
# ==============================================================================

ARTIFACTS_DIR = settings.CAR_DETECTOR_DIR
"""Dossier contenant les artifacts du modèle"""

MODEL_PATH = settings.CAR_MODEL_PATH
"""Chemin du modèle .h5"""

SCALER_PATH = settings.CAR_SCALER_PATH
"""Chemin du scaler .pkl"""

FEATURES_PATH = settings.CAR_FEATURES_PATH
"""Chemin de la liste des features"""


# ==============================================================================
# DONNÉES D'ENTRAÎNEMENT
# ==============================================================================

DATA_DIR = settings.DATA_DIR / "car_detector"
"""Dossier des données pour ce modèle"""

# Slices partagés OU spécifiques au modèle
SHARED_SLICES_DIR = settings.DATA_DIR / "slices"
"""Dossier commun des slices (si partagé entre modèles)"""

SLICES_DIR = SHARED_SLICES_DIR if SHARED_SLICES_DIR.exists() else DATA_DIR / "slices"
"""Dossier des slices audio (commun ou spécifique)"""

ANNOTATION_CSV = DATA_DIR / "annotation.csv"
"""Fichier d'annotations (nfile, label: 0=pas voiture, 1=voiture)"""

FEATURES_CSV = DATA_DIR / "features.csv"
"""Fichier des features extraites"""


# ==============================================================================
# PARAMÈTRES DU MODÈLE
# ==============================================================================

DETECTION_THRESHOLD = settings.CAR_DETECTION_THRESHOLD
"""Seuil de détection (probabilité > seuil = voiture détectée)"""

POSITIVE_LABEL = "VOITURE"
"""Label pour la classe positive (voiture détectée)"""

NEGATIVE_LABEL = "PAS_VOITURE"
"""Label pour la classe négative"""


# ==============================================================================
# TOP FEATURES (à mettre à jour après analyse)
# ==============================================================================

DEFAULT_TOP_FEATURES = [
    'mfcc_1_mean', 'mfcc_2_mean', 'mfcc_3_mean', 'mfcc_4_mean',
    'mfcc_5_mean', 'mfcc_6_mean', 'spectral_centroid_mean',
    'spectral_bandwidth_mean', 'spectral_rolloff_mean',
    'zcr_mean', 'rms_mean', 'chroma_mean'
]
"""Features par défaut si pas de fichier d'importance disponible"""
