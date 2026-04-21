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


def load_melspectrogram(path: str, sr: int, duration: float,
                        n_mels: int, n_fft: int, hop_length: int):
    """
    Charge un fichier audio et retourne son mel-spectrogramme en dB.

    Paramètres:
        path:       Chemin vers le fichier audio
        sr:         Sample rate cible (Hz)
        duration:   Durée cible en secondes (tronque ou pad)
        n_mels:     Nombre de bandes mel
        n_fft:      Taille FFT
        hop_length: Pas du STFT

    Retourne:
        np.ndarray de shape (n_mels, n_frames) en dB, ou None si erreur.
    """
    try:
        y, _ = librosa.load(str(path), sr=sr, duration=duration)
        target_len = int(sr * duration)
        if len(y) < sr * 0.5:
            return None
        if len(y) < target_len:
            y = np.pad(y, (0, target_len - len(y)), mode='constant')
        else:
            y = y[:target_len]
        y = librosa.util.normalize(y)
        mel = librosa.feature.melspectrogram(
            y=y, sr=sr, n_mels=n_mels, n_fft=n_fft, hop_length=hop_length
        )
        return librosa.power_to_db(mel, ref=np.max)
    except Exception:
        return None


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


def extract_vehicle_features(y: np.ndarray, sr: int = None) -> dict:
    """
    Extrait des features spécifiques pour la détection de véhicules.

    Ces features sont optimisées pour capturer les caractéristiques
    acoustiques des moteurs et échappements de véhicules :
    - Énergie basses fréquences (moteur: 20-200 Hz)
    - Delta MFCC (changements temporels)
    - Mel spectrogram par bande de fréquence
    - Onset strength (attaques sonores)
    - Spectral flux (changements spectraux)

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
    # 1. ÉNERGIE PAR BANDE DE FRÉQUENCE (crucial pour moteurs)
    # ==========================================================================

    S = np.abs(librosa.stft(y))
    freqs = librosa.fft_frequencies(sr=sr)

    # Bandes: très basses (20-100Hz), basses (100-300Hz), mediums (300-2000Hz), hautes (>2000Hz)
    very_low_mask = (freqs >= 20) & (freqs < 100)
    low_mask = (freqs >= 100) & (freqs < 300)
    mid_mask = (freqs >= 300) & (freqs < 2000)
    high_mask = freqs >= 2000

    features['very_low_freq_energy'] = float(np.mean(S[very_low_mask, :])) if very_low_mask.any() else 0.0
    features['low_freq_energy'] = float(np.mean(S[low_mask, :])) if low_mask.any() else 0.0
    features['mid_freq_energy'] = float(np.mean(S[mid_mask, :])) if mid_mask.any() else 0.0
    features['high_freq_energy'] = float(np.mean(S[high_mask, :])) if high_mask.any() else 0.0

    # Ratios d'énergie (caractéristiques des moteurs)
    total_energy = features['very_low_freq_energy'] + features['low_freq_energy'] + features['mid_freq_energy'] + features['high_freq_energy'] + 1e-10
    features['low_freq_ratio'] = (features['very_low_freq_energy'] + features['low_freq_energy']) / total_energy
    features['low_high_ratio'] = (features['very_low_freq_energy'] + features['low_freq_energy']) / (features['high_freq_energy'] + 1e-10)

    # ==========================================================================
    # 2. DELTA MFCC (changements temporels - important pour sons de moteur)
    # ==========================================================================

    mfccs = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=13)
    delta_mfcc = librosa.feature.delta(mfccs)
    delta2_mfcc = librosa.feature.delta(mfccs, order=2)

    for i in range(13):
        features[f'delta_mfcc_{i+1}_mean'] = float(np.mean(delta_mfcc[i]))
        features[f'delta_mfcc_{i+1}_std'] = float(np.std(delta_mfcc[i]))
        features[f'delta2_mfcc_{i+1}_mean'] = float(np.mean(delta2_mfcc[i]))

    # ==========================================================================
    # 3. MEL SPECTROGRAM PAR BANDE
    # ==========================================================================

    mel_spec = librosa.feature.melspectrogram(y=y, sr=sr, n_mels=128)
    mel_db = librosa.power_to_db(mel_spec, ref=np.max)

    # Bandes: 0-10 (très basses), 10-30 (basses), 30-60 (mediums), 60-128 (hautes)
    features['mel_very_low_mean'] = float(np.mean(mel_db[:10, :]))
    features['mel_very_low_std'] = float(np.std(mel_db[:10, :]))
    features['mel_low_mean'] = float(np.mean(mel_db[10:30, :]))
    features['mel_low_std'] = float(np.std(mel_db[10:30, :]))
    features['mel_mid_mean'] = float(np.mean(mel_db[30:60, :]))
    features['mel_mid_std'] = float(np.std(mel_db[30:60, :]))
    features['mel_high_mean'] = float(np.mean(mel_db[60:, :]))
    features['mel_high_std'] = float(np.std(mel_db[60:, :]))

    # Variation temporelle du mel spectrogram
    mel_diff = np.diff(mel_db, axis=1)
    features['mel_temporal_var_mean'] = float(np.mean(np.abs(mel_diff)))
    features['mel_temporal_var_std'] = float(np.std(np.abs(mel_diff)))

    # ==========================================================================
    # 4. ONSET STRENGTH (détection d'attaques/transitoires)
    # ==========================================================================

    onset_env = librosa.onset.onset_strength(y=y, sr=sr)
    features['onset_mean'] = float(np.mean(onset_env))
    features['onset_std'] = float(np.std(onset_env))
    features['onset_max'] = float(np.max(onset_env))
    features['onset_min'] = float(np.min(onset_env))

    # Nombre de pics d'onset (transitoires)
    onset_peaks = librosa.util.peak_pick(onset_env, pre_max=3, post_max=3, pre_avg=3, post_avg=5, delta=0.5, wait=10)
    features['onset_peaks_count'] = float(len(onset_peaks))
    features['onset_peaks_rate'] = float(len(onset_peaks) / (len(y) / sr))  # peaks per second

    # ==========================================================================
    # 5. SPECTRAL FLUX (changement spectral dans le temps)
    # ==========================================================================

    spectral_flux = np.sqrt(np.sum(np.diff(S, axis=1)**2, axis=0))
    features['spectral_flux_mean'] = float(np.mean(spectral_flux))
    features['spectral_flux_std'] = float(np.std(spectral_flux))
    features['spectral_flux_max'] = float(np.max(spectral_flux))

    # ==========================================================================
    # 6. AUTOCORRELATION (périodicité - caractéristique des moteurs)
    # ==========================================================================

    # Autocorrelation pour détecter la périodicité du signal
    autocorr = librosa.autocorrelate(y, max_size=sr // 10)  # Max 100ms lag
    autocorr = autocorr / (autocorr[0] + 1e-10)  # Normaliser

    # Trouver les pics d'autocorrelation (périodicité)
    if len(autocorr) > 10:
        features['autocorr_peak_value'] = float(np.max(autocorr[10:]))  # Ignorer le pic à 0
        features['autocorr_mean'] = float(np.mean(autocorr[10:]))
    else:
        features['autocorr_peak_value'] = 0.0
        features['autocorr_mean'] = 0.0

    return features


def extract_noise_features(y: np.ndarray, sr: int = None) -> dict:
    """
    Extrait des features spécifiques pour la détection de véhicules BRUYANTS.

    Ces features capturent les caractéristiques des véhicules bruyants/rapides :
    - Pics de décibels et variations
    - Énergie haute fréquence (échappement bruyant)
    - Crest factor (agressivité du son)
    - Ratio percussif/harmonique
    - Fréquence fondamentale (F0) / RPM estimation
    - Harmonic-to-Noise Ratio (HNR)
    - Power Spectral Density par bandes
    - Spectral tone-pitch features

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
    # 0. FRÉQUENCE FONDAMENTALE (F0) - Estimation RPM moteur
    # ==========================================================================

    # Utilise pyin pour détecter F0 (plus robuste que yin pour moteurs)
    try:
        f0, voiced_flag, voiced_probs = librosa.pyin(
            y, fmin=50, fmax=500, sr=sr  # Moteurs: 50-500 Hz
        )
        f0_valid = f0[~np.isnan(f0)]
        if len(f0_valid) > 0:
            features['f0_mean'] = float(np.mean(f0_valid))
            features['f0_std'] = float(np.std(f0_valid))
            features['f0_min'] = float(np.min(f0_valid))
            features['f0_max'] = float(np.max(f0_valid))
            features['f0_range'] = float(np.max(f0_valid) - np.min(f0_valid))
            # Estimation RPM approximative (F0 * 60 pour 2-temps, F0 * 120 pour 4-temps)
            features['estimated_rpm'] = float(np.mean(f0_valid) * 60)
        else:
            features['f0_mean'] = 0.0
            features['f0_std'] = 0.0
            features['f0_min'] = 0.0
            features['f0_max'] = 0.0
            features['f0_range'] = 0.0
            features['estimated_rpm'] = 0.0

        # Ratio de frames voisées (présence de ton)
        features['voiced_ratio'] = float(np.mean(voiced_probs[~np.isnan(voiced_probs)]))
    except:
        features['f0_mean'] = 0.0
        features['f0_std'] = 0.0
        features['f0_min'] = 0.0
        features['f0_max'] = 0.0
        features['f0_range'] = 0.0
        features['estimated_rpm'] = 0.0
        features['voiced_ratio'] = 0.0

    # ==========================================================================
    # 0b. HARMONIC-TO-NOISE RATIO (HNR) - Qualité tonale
    # ==========================================================================

    y_harm, y_noise = librosa.effects.hpss(y)
    harm_power = np.sum(y_harm**2)
    noise_power = np.sum((y - y_harm)**2)

    # HNR en dB
    hnr = 10 * np.log10(harm_power / (noise_power + 1e-10))
    features['hnr_db'] = float(hnr)

    # HNR par frame (variation temporelle)
    frame_length = 2048
    hop_length = 512
    hnr_frames = []
    for i in range(0, len(y) - frame_length, hop_length):
        frame = y[i:i + frame_length]
        frame_harm, _ = librosa.effects.hpss(frame)
        h_pow = np.sum(frame_harm**2)
        n_pow = np.sum((frame - frame_harm)**2) + 1e-10
        hnr_frames.append(10 * np.log10(h_pow / n_pow + 1e-10))

    if hnr_frames:
        features['hnr_mean'] = float(np.mean(hnr_frames))
        features['hnr_std'] = float(np.std(hnr_frames))
    else:
        features['hnr_mean'] = float(hnr)
        features['hnr_std'] = 0.0

    # ==========================================================================
    # 0c. POWER SPECTRAL DENSITY (PSD) PAR BANDES SPÉCIFIQUES
    # ==========================================================================

    # PSD via Welch method
    from scipy import signal as scipy_signal
    freqs_psd, psd = scipy_signal.welch(y, sr, nperseg=2048)

    # Bandes spécifiques moteur/échappement
    # 50-150 Hz: Fondamentale moteur basse
    # 150-300 Hz: Fondamentale moteur haute / harmoniques
    # 300-800 Hz: Harmoniques moteur
    # 800-2000 Hz: Échappement
    # 2000-4000 Hz: Sifflement turbo / échappement sport
    # 4000-8000 Hz: Bruit aérodynamique / pneus

    bands = [
        ('psd_motor_low', 50, 150),
        ('psd_motor_high', 150, 300),
        ('psd_harmonics', 300, 800),
        ('psd_exhaust', 800, 2000),
        ('psd_turbo', 2000, 4000),
        ('psd_aero', 4000, 8000),
    ]

    for name, fmin, fmax in bands:
        mask = (freqs_psd >= fmin) & (freqs_psd < fmax)
        if mask.any():
            features[name] = float(np.mean(psd[mask]))
        else:
            features[name] = 0.0

    # Ratio PSD basses/hautes fréquences
    low_psd = features['psd_motor_low'] + features['psd_motor_high']
    high_psd = features['psd_turbo'] + features['psd_aero'] + 1e-10
    features['psd_low_high_ratio'] = float(low_psd / high_psd)

    # ==========================================================================
    # 0d. SPECTRAL TONE-PITCH FEATURES (Pics tonaux)
    # ==========================================================================

    # Détection des pics spectraux (tons purs du moteur)
    S = np.abs(librosa.stft(y))
    S_mean = np.mean(S, axis=1)

    # Trouver les pics spectraux proéminents
    from scipy.signal import find_peaks
    peaks, properties = find_peaks(S_mean, height=np.mean(S_mean), prominence=np.std(S_mean))

    features['spectral_peaks_count'] = float(len(peaks))

    if len(peaks) > 0 and 'peak_heights' in properties:
        features['spectral_peaks_mean_height'] = float(np.mean(properties['peak_heights']))
        features['spectral_peaks_max_height'] = float(np.max(properties['peak_heights']))

        # Fréquence des pics principaux
        freqs_stft = librosa.fft_frequencies(sr=sr)
        peak_freqs = freqs_stft[peaks]
        features['dominant_peak_freq'] = float(peak_freqs[np.argmax(properties['peak_heights'])])
    else:
        features['spectral_peaks_mean_height'] = 0.0
        features['spectral_peaks_max_height'] = 0.0
        features['dominant_peak_freq'] = 0.0

    # ==========================================================================
    # 1. ANALYSE DES DÉCIBELS ET PICS
    # ==========================================================================

    rms = librosa.feature.rms(y=y)[0]
    rms_db = librosa.amplitude_to_db(rms + 1e-10)

    features['db_mean'] = float(np.mean(rms_db))
    features['db_max'] = float(np.max(rms_db))
    features['db_min'] = float(np.min(rms_db))
    features['db_std'] = float(np.std(rms_db))
    features['db_range'] = float(np.max(rms_db) - np.min(rms_db))

    # Pics de volume
    db_threshold = np.mean(rms_db) + np.std(rms_db)
    db_peaks = np.sum(rms_db > db_threshold)
    features['db_peaks_count'] = float(db_peaks)
    features['db_peaks_ratio'] = float(db_peaks / len(rms_db))

    # ==========================================================================
    # 2. CREST FACTOR (rapport pic/RMS - indicateur d'impulsivité)
    # ==========================================================================

    peak_amplitude = np.max(np.abs(y))
    rms_total = np.sqrt(np.mean(y**2))
    crest_factor = peak_amplitude / (rms_total + 1e-10)

    features['crest_factor'] = float(crest_factor)
    features['crest_factor_db'] = float(20 * np.log10(crest_factor + 1e-10))

    # ==========================================================================
    # 3. ÉNERGIE HAUTE FRÉQUENCE (échappements bruyants)
    # ==========================================================================

    S = np.abs(librosa.stft(y))
    freqs = librosa.fft_frequencies(sr=sr)

    high_mask = (freqs >= 2000) & (freqs < 8000)
    very_high_mask = freqs >= 8000
    low_mask = freqs < 500

    high_energy = float(np.mean(S[high_mask, :])) if high_mask.any() else 0.0
    very_high_energy = float(np.mean(S[very_high_mask, :])) if very_high_mask.any() else 0.0
    low_energy = float(np.mean(S[low_mask, :])) if low_mask.any() else 1e-10

    features['high_freq_2k_8k'] = high_energy
    features['very_high_freq_8k'] = very_high_energy
    features['high_low_energy_ratio'] = (high_energy + very_high_energy) / (low_energy + 1e-10)

    # ==========================================================================
    # 4. SPECTRAL CONTRAST (agressivité sonore)
    # ==========================================================================

    contrast = librosa.feature.spectral_contrast(y=y, sr=sr)
    features['spectral_contrast_mean'] = float(np.mean(contrast))
    features['spectral_contrast_std'] = float(np.std(contrast))
    features['spectral_contrast_max'] = float(np.max(contrast))

    # Spectral rolloff 95%
    rolloff = librosa.feature.spectral_rolloff(y=y, sr=sr, roll_percent=0.95)[0]
    features['spectral_rolloff_95_mean'] = float(np.mean(rolloff))
    features['spectral_rolloff_95_std'] = float(np.std(rolloff))

    # ==========================================================================
    # 5. VARIATIONS TEMPORELLES
    # ==========================================================================

    rms_diff = np.diff(rms)
    features['rms_variation_mean'] = float(np.mean(np.abs(rms_diff)))
    features['rms_variation_max'] = float(np.max(np.abs(rms_diff)))

    zcr = librosa.feature.zero_crossing_rate(y)[0]
    features['zcr_noise_mean'] = float(np.mean(zcr))
    features['zcr_noise_std'] = float(np.std(zcr))
    features['zcr_noise_max'] = float(np.max(zcr))

    # ==========================================================================
    # 6. HARMONIC-PERCUSSIVE RATIO
    # ==========================================================================

    y_harm, y_perc = librosa.effects.hpss(y)
    perc_energy = np.sum(y_perc**2)
    harm_energy = np.sum(y_harm**2)
    total_energy = perc_energy + harm_energy + 1e-10

    features['percussive_ratio'] = float(perc_energy / total_energy)
    features['perc_harm_ratio'] = float(perc_energy / (harm_energy + 1e-10))

    return features


def extract_all_features(y: np.ndarray, sr: int = None) -> dict:
    """
    Extrait toutes les features (base + véhicule + bruit).

    Combine extract_base_features, extract_vehicle_features et extract_noise_features.

    Paramètres:
        y (np.ndarray): Signal audio
        sr (int): Sample rate (défaut: settings.SAMPLE_RATE)

    Retourne:
        dict: Dictionnaire {nom_feature: valeur}
    """
    if sr is None:
        sr = settings.SAMPLE_RATE

    # Features de base
    features = extract_base_features(y, sr)

    # Features spécifiques véhicules
    vehicle_features = extract_vehicle_features(y, sr)
    features.update(vehicle_features)

    # Features spécifiques bruit
    noise_features = extract_noise_features(y, sr)
    features.update(noise_features)

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
