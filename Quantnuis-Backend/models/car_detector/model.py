#!/usr/bin/env python3
"""
================================================================================
                    MODÈLE - DÉTECTION VOITURE
================================================================================

Classe principale pour la détection de voiture dans un fichier audio.

Supporte deux backends :
  1. CRNN sur mel-spectrogrammes (prioritaire)
  2. MLP sur features manuelles (fallback)

Le CRNN est utilisé automatiquement si les artifacts sont présents
(crnn_car_detector.h5 + crnn_config.json). Sinon, le MLP classique est utilisé.

Usage:
    from models.car_detector import CarDetector

    detector = CarDetector()
    detector.load()

    label, confidence, prob = detector.predict_file("audio.wav")
    print(f"{label}: {confidence:.1f}%")

================================================================================
"""

import os
import json
import numpy as np
from pathlib import Path
from typing import Tuple, Optional

from models.base_model import BaseMLModel
from config import get_settings
from shared import (
    print_header, print_success, print_info,
    print_warning, print_error, Colors,
    load_audio, normalize_audio, extract_base_features, select_features
)
from . import config

settings = get_settings()


class CarDetector(BaseMLModel):
    """
    Modèle de détection de voiture.

    Détecte si un fichier audio contient le son d'une voiture ou non.

    Supporte deux modes :
      - CRNN : mel-spectrogramme → Conv2D+LSTM → classification (prioritaire)
      - MLP  : features manuelles → Dense → classification (fallback)

    Usage:
        detector = CarDetector()
        label, confidence, prob = detector.predict_file("audio.wav")
    """

    def __init__(self):
        """Initialise le détecteur de voiture."""
        super().__init__("CarDetector")
        self._use_crnn = False
        self._crnn_config = None

    # ==========================================================================
    # PROPRIÉTÉS (implémentation des abstractions)
    # ==========================================================================

    @property
    def model_path(self) -> Path:
        return config.MODEL_PATH

    @property
    def scaler_path(self) -> Path:
        return config.SCALER_PATH

    @property
    def features_path(self) -> Path:
        return config.FEATURES_PATH

    @property
    def threshold(self) -> float:
        return config.DETECTION_THRESHOLD

    @property
    def positive_label(self) -> str:
        return config.POSITIVE_LABEL

    @property
    def negative_label(self) -> str:
        return config.NEGATIVE_LABEL

    @property
    def use_crnn(self) -> bool:
        """Indique si le modèle utilise le CRNN."""
        return self._use_crnn

    # ==========================================================================
    # CHARGEMENT (override pour supporter CRNN)
    # ==========================================================================

    def load(self) -> bool:
        """
        Charge le modèle. Priorité au CRNN si les artifacts sont présents.

        Ordre de priorité :
          1. CRNN (crnn_car_detector.h5 + crnn_config.json)
          2. MLP classique (model.h5 + scaler.pkl + features.txt)
        """
        if self._is_loaded:
            return True

        # Tenter le CRNN d'abord
        if self._load_crnn():
            return True

        # Fallback sur le MLP classique
        print_info(f"[{self.model_name}] CRNN non disponible, fallback sur MLP")
        return super().load()

    def _load_crnn(self) -> bool:
        """Charge le modèle CRNN et sa configuration."""
        import tensorflow as tf

        crnn_model_path = config.CRNN_MODEL_PATH
        crnn_config_path = config.CRNN_CONFIG_PATH

        if not crnn_model_path.exists():
            return False
        if not crnn_config_path.exists():
            print_warning(f"[{self.model_name}] CRNN model trouvé mais config manquante: {crnn_config_path}")
            return False

        try:
            # Charger la config
            with open(crnn_config_path, 'r') as f:
                self._crnn_config = json.load(f)

            # Charger le modèle
            self.model = tf.keras.models.load_model(str(crnn_model_path))

            self._use_crnn = True
            self._is_loaded = True

            print_success(
                f"[{self.model_name}] CRNN chargé "
                f"(F1={self._crnn_config.get('cv_f1_mean', '?'):.4f}, "
                f"{self._crnn_config.get('n_samples', '?')} samples)"
            )

            return True

        except Exception as e:
            print_error(f"[{self.model_name}] Erreur chargement CRNN: {e}")
            self._use_crnn = False
            return False

    # ==========================================================================
    # PRÉDICTION
    # ==========================================================================

    def predict_file(self, audio_path: str, verbose: bool = False) -> Tuple[str, float, float]:
        """
        Prédit si un fichier audio contient une voiture.

        Utilise le CRNN (spectrogramme) ou le MLP (features) selon le modèle chargé.

        Paramètres:
            audio_path (str): Chemin vers le fichier audio
            verbose (bool): Afficher les détails de la prédiction

        Retourne:
            tuple: (label, confiance_pourcentage, probabilité_brute)

            - label: "VOITURE" ou "PAS_VOITURE"
            - confiance: Pourcentage de confiance (0-100)
            - probabilité: Valeur brute sigmoid (0-1)
        """
        if not os.path.exists(audio_path):
            print_error(f"Fichier non trouvé: {audio_path}")
            raise FileNotFoundError(audio_path)

        if not self.ensure_loaded():
            raise RuntimeError("Impossible de charger le modèle CarDetector")

        if verbose:
            mode = "CRNN/spectrogramme" if self._use_crnn else "MLP/features"
            print_header(f"Détection Voiture ({mode})")
            print_info(f"Fichier: {audio_path}")

        if self._use_crnn:
            label, confidence, probability = self._predict_crnn(audio_path, verbose)
        else:
            label, confidence, probability = self._predict_mlp(audio_path, verbose)

        if verbose:
            self._display_result(label, confidence, probability)

        return label, confidence, probability

    def _predict_crnn(self, audio_path: str, verbose: bool = False) -> Tuple[str, float, float]:
        """Prédiction via CRNN sur mel-spectrogramme."""
        import librosa

        cfg = self._crnn_config
        sr = cfg.get('sr', 22050)
        duration = cfg.get('duration', 4.0)
        n_mels = cfg.get('n_mels', 128)
        n_fft = cfg.get('n_fft', 2048)
        hop_length = cfg.get('hop_length', 512)
        x_mean = cfg.get('X_mean', 0.0)
        x_std = cfg.get('X_std', 1.0)

        if verbose:
            print_info(f"Création mel-spectrogramme ({n_mels} mels, {sr} Hz, {duration}s)")

        # Charger et préparer l'audio
        y, _ = librosa.load(audio_path, sr=sr, duration=duration)

        # Pad/tronquer à la durée exacte
        target_len = int(sr * duration)
        if len(y) < target_len:
            y = np.pad(y, (0, target_len - len(y)), mode='constant')
        else:
            y = y[:target_len]

        # Normaliser l'audio
        y = librosa.util.normalize(y)

        # Calculer le mel-spectrogramme
        mel = librosa.feature.melspectrogram(
            y=y, sr=sr, n_mels=n_mels, n_fft=n_fft, hop_length=hop_length
        )
        mel_db = librosa.power_to_db(mel, ref=np.max)

        # Normaliser avec les stats du dataset d'entraînement
        mel_norm = (mel_db - x_mean) / (x_std + 1e-8)

        # Préparer le batch : (1, n_mels, time, 1)
        X = mel_norm[np.newaxis, ..., np.newaxis]

        if verbose:
            print_info(f"Input shape: {X.shape}")

        # Prédire
        probability = float(self.model.predict(X, verbose=0)[0][0])

        # Interpréter
        if probability > self.threshold:
            label = self.positive_label
            confidence = probability * 100
        else:
            label = self.negative_label
            confidence = (1 - probability) * 100

        return label, confidence, probability

    def _predict_mlp(self, audio_path: str, verbose: bool = False) -> Tuple[str, float, float]:
        """Prédiction via MLP sur features manuelles (ancien pipeline)."""
        if verbose:
            print_info("Extraction des features...")

        y, sr = load_audio(audio_path)
        y = normalize_audio(y)
        all_features = extract_base_features(y, sr)
        features = select_features(all_features, self.feature_names)

        return self.predict_features(features)

    # ==========================================================================
    # AFFICHAGE
    # ==========================================================================

    def _display_result(self, label: str, confidence: float, probability: float):
        """Affiche le résultat de la prédiction."""
        print()
        mode_str = "CRNN" if self._use_crnn else "MLP"
        print(f"  {Colors.BOLD}Résultat ({mode_str}):{Colors.END}")

        if label == self.positive_label:
            color = Colors.GREEN
            emoji = "🚗"
        else:
            color = Colors.CYAN
            emoji = "✓"

        print()
        print(f"    {color}{Colors.BOLD}┌─────────────────────────────────┐{Colors.END}")
        print(f"    {color}{Colors.BOLD}│                                 │{Colors.END}")
        print(f"    {color}{Colors.BOLD}│   {emoji}  {label:^20}  {emoji}   │{Colors.END}")
        print(f"    {color}{Colors.BOLD}│                                 │{Colors.END}")
        print(f"    {color}{Colors.BOLD}│      Confiance: {confidence:>5.1f}%          │{Colors.END}")
        print(f"    {color}{Colors.BOLD}│                                 │{Colors.END}")
        print(f"    {color}{Colors.BOLD}└─────────────────────────────────┘{Colors.END}")
        print()

        # Barre de progression
        bar_len = int(confidence / 5)
        bar = '█' * bar_len + '░' * (20 - bar_len)
        print(f"    Confiance: [{bar}] {confidence:.1f}%")

        print()
        print(f"    {Colors.DIM}Score brut (sigmoid): {probability:.4f}{Colors.END}")
        print(f"    {Colors.DIM}Seuil de décision: {self.threshold}{Colors.END}")
        print(f"    {Colors.DIM}Backend: {mode_str}{Colors.END}")

    # ==========================================================================
    # INFO
    # ==========================================================================

    def get_model_info(self) -> dict:
        """Retourne les informations sur le modèle."""
        info = super().get_model_info()
        info["backend"] = "CRNN" if self._use_crnn else "MLP"
        if self._use_crnn and self._crnn_config:
            info["crnn_f1"] = self._crnn_config.get("cv_f1_mean")
            info["crnn_samples"] = self._crnn_config.get("n_samples")
            info["input_shape"] = self._crnn_config.get("input_shape")
        return info


# ==============================================================================
# POINT D'ENTRÉE CLI
# ==============================================================================

def main():
    """Point d'entrée en ligne de commande."""
    import sys

    if len(sys.argv) < 2:
        print(f"""
{Colors.BOLD}CarDetector - Détection de voiture dans un fichier audio{Colors.END}

{Colors.CYAN}Usage:{Colors.END}
    python -m models.car_detector.model <fichier_audio>
    python -m models.car_detector.model audio.wav

{Colors.CYAN}Backends:{Colors.END}
    CRNN (mel-spectrogrammes) : Utilisé si crnn_car_detector.h5 est présent
    MLP (features manuelles)  : Fallback sinon

{Colors.CYAN}Formats supportés:{Colors.END}
    .wav, .mp3, .flac, .ogg, .m4a
        """)
        sys.exit(1)

    audio_path = sys.argv[1]

    detector = CarDetector()
    label, confidence, prob = detector.predict_file(audio_path, verbose=True)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}[!]{Colors.END} Annulé")
    except Exception as e:
        print_error(str(e))
        raise
