#!/usr/bin/env python3
"""
================================================================================
                    UTILITAIRES AUDIO
================================================================================

Fonctions partagées pour le traitement audio utilisées par les deux modèles.

================================================================================
"""

import warnings
import numpy as np
import librosa

from config import get_settings

warnings.filterwarnings('ignore')

settings = get_settings()


def load_audio(file_path: str, sr: int = None) -> tuple:
    """
    Charge un fichier audio.
    
    Paramètres:
        file_path (str): Chemin vers le fichier audio
        sr (int): Sample rate souhaité (défaut: settings.SAMPLE_RATE)
    
    Retourne:
        tuple: (signal_audio, sample_rate)
    
    Note:
        - Convertit automatiquement en mono si stéréo
        - Rééchantillonne à la fréquence demandée
    """
    if sr is None:
        sr = settings.SAMPLE_RATE
    
    y, actual_sr = librosa.load(file_path, sr=sr)
    return y, actual_sr


def normalize_audio(y: np.ndarray) -> np.ndarray:
    """
    Normalise le signal audio entre -1 et 1.
    
    Paramètres:
        y (np.ndarray): Signal audio
    
    Retourne:
        np.ndarray: Signal normalisé
    """
    return librosa.util.normalize(y)


def extract_base_features(y: np.ndarray, sr: int = None) -> dict:
    """
    Extrait les caractéristiques audio de base.
    
    Cette fonction extrait ~100 features audio utilisables par les modèles.
    Les deux modèles (car_detector et noisy_car_detector) partagent cette base.
    
    Catégories de features :
    1. Temporelles (RMS, ZCR)
    2. Spectrales (centroid, bandwidth, rolloff, flatness, contrast)
    3. Harmoniques / Percussives
    4. MFCC (40 coefficients)
    5. Chroma (12 notes)
    6. Tempo et énergie
    
    Paramètres:
        y (np.ndarray): Signal audio
        sr (int): Sample rate (défaut: settings.SAMPLE_RATE)
    
    Retourne:
        dict: Dictionnaire {nom_feature: valeur}
    """
    if sr is None:
        sr = settings.SAMPLE_RATE
    
    features = {}
    
    # ==========================================================================
    # 1. FEATURES TEMPORELLES
    # ==========================================================================
    
    # RMS (Root Mean Square) - Volume moyen
    rms = librosa.feature.rms(y=y)[0]
    features['rms_mean'] = float(np.mean(rms))
    features['rms_std'] = float(np.std(rms))
    
    # Zero Crossing Rate - Taux de passage par zéro
    zcr = librosa.feature.zero_crossing_rate(y)[0]
    features['zcr_mean'] = float(np.mean(zcr))
    features['zcr_std'] = float(np.std(zcr))
    
    # ==========================================================================
    # 2. FEATURES SPECTRALES
    # ==========================================================================
    
    # Spectral Centroid - Centre de gravité du spectre
    spectral_centroids = librosa.feature.spectral_centroid(y=y, sr=sr)[0]
    features['spectral_centroid_mean'] = float(np.mean(spectral_centroids))
    features['spectral_centroid_std'] = float(np.std(spectral_centroids))
    
    # Spectral Bandwidth - Largeur du spectre
    spectral_bandwidth = librosa.feature.spectral_bandwidth(y=y, sr=sr)[0]
    features['spectral_bandwidth_mean'] = float(np.mean(spectral_bandwidth))
    features['spectral_bandwidth_std'] = float(np.std(spectral_bandwidth))
    
    # Spectral Rolloff - Fréquence de coupure (85% énergie)
    spectral_rolloff = librosa.feature.spectral_rolloff(y=y, sr=sr)[0]
    features['spectral_rolloff_mean'] = float(np.mean(spectral_rolloff))
    features['spectral_rolloff_std'] = float(np.std(spectral_rolloff))
    
    # Spectral Flatness - Bruit blanc vs son tonal
    spectral_flatness = librosa.feature.spectral_flatness(y=y)[0]
    features['spectral_flatness_mean'] = float(np.mean(spectral_flatness))
    features['spectral_flatness_std'] = float(np.std(spectral_flatness))
    
    # Spectral Contrast - Différence pics/creux
    spectral_contrast = librosa.feature.spectral_contrast(y=y, sr=sr)
    features['spectral_contrast_mean'] = float(np.mean(spectral_contrast))
    features['spectral_contrast_std'] = float(np.std(spectral_contrast))
    
    # ==========================================================================
    # 3. HARMONIQUES / PERCUSSIVES
    # ==========================================================================
    
    harmonic, percussive = librosa.effects.hpss(y)
    
    features['harm_mean'] = float(np.mean(np.abs(harmonic)))
    features['harm_std'] = float(np.std(harmonic))
    features['perc_mean'] = float(np.mean(np.abs(percussive)))
    features['perc_std'] = float(np.std(percussive))
    
    # Ratio harmonique/percussif
    features['harm_perc_ratio'] = float(
        np.mean(np.abs(harmonic)) / (np.mean(np.abs(percussive)) + 1e-10)
    )
    
    # ==========================================================================
    # 4. MFCC (Mel-Frequency Cepstral Coefficients)
    # ==========================================================================
    
    n_mfcc = settings.N_MFCC
    mfccs = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=n_mfcc)
    
    for i in range(n_mfcc):
        features[f'mfcc_{i+1}_mean'] = float(np.mean(mfccs[i]))
        features[f'mfcc_{i+1}_std'] = float(np.std(mfccs[i]))
    
    # ==========================================================================
    # 5. CHROMA (Notes musicales)
    # ==========================================================================
    
    chroma = librosa.feature.chroma_stft(y=y, sr=sr)
    features['chroma_mean'] = float(np.mean(chroma))
    features['chroma_std'] = float(np.std(chroma))
    
    for i in range(12):
        features[f'chroma_{i}_mean'] = float(np.mean(chroma[i]))
    
    # ==========================================================================
    # 6. TEMPO ET ÉNERGIE
    # ==========================================================================
    
    try:
        tempo, _ = librosa.beat.beat_track(y=y, sr=sr)
        features['tempo'] = float(np.asarray(tempo).item() if np.ndim(tempo) > 0 else tempo)
    except:
        features['tempo'] = 0.0
    
    features['energy'] = float(np.sum(y**2))
    features['max_amplitude'] = float(np.max(np.abs(y)))
    
    return features


def select_features(all_features: dict, feature_names: list) -> dict:
    """
    Sélectionne un sous-ensemble de features.
    
    Paramètres:
        all_features (dict): Toutes les features extraites
        feature_names (list): Liste des noms de features à garder
    
    Retourne:
        dict: Features sélectionnées
    """
    selected = {}
    
    for name in feature_names:
        if name in all_features:
            selected[name] = all_features[name]
        else:
            selected[name] = 0.0
    
    return selected
