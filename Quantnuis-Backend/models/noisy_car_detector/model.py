#!/usr/bin/env python3
"""
================================================================================
                    MODÈLE - VOITURE BRUYANTE
================================================================================

Classe principale pour la détection de voiture bruyante.

Supporte deux backends :
  1. CNN sur mel-spectrogrammes (prioritaire, F1=0.994)
  2. MLP sur features manuelles (fallback, F1=0.962)

Le CNN est utilisé automatiquement si les artifacts sont présents
(cnn_noisy_car.h5 + cnn_config.json). Sinon, le MLP classique est utilisé.

Ce modèle ne doit être utilisé que sur des audios où une voiture
a DÉJÀ été détectée par le modèle car_detector.

Usage:
    from models.noisy_car_detector import NoisyCarDetector

    detector = NoisyCarDetector()
    detector.load()

    label, confidence, prob = detector.predict_file("audio_with_car.wav")
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


class NoisyCarDetector(BaseMLModel):
    """
    Modèle de détection de voiture bruyante.

    Détecte si une voiture (déjà identifiée) est bruyante ou non.

    Supporte deux modes :
      - CNN : mel-spectrogramme → Conv2D → classification (prioritaire)
      - MLP : 225 features → Dense → classification (fallback)

    IMPORTANT: Ce modèle ne doit être utilisé que sur des audios
    où une voiture a déjà été détectée par CarDetector.
    """

    def __init__(self):
        """Initialise le détecteur de voiture bruyante."""
        super().__init__("NoisyCarDetector")
        self._use_cnn = False
        self._cnn_config = None

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
    def use_cnn(self) -> bool:
        """Indique si le modèle utilise le CNN."""
        return self._use_cnn

    # ==========================================================================
    # CHARGEMENT (override pour supporter CNN)
    # ==========================================================================

    def load(self) -> bool:
        """
        Charge le modèle. Priorité au CNN si les artifacts sont présents.

        Ordre de priorité :
          1. CNN (cnn_noisy_car.h5 + cnn_config.json)
          2. MLP classique (model.h5 + scaler.pkl + features.txt)
        """
        if self._is_loaded:
            return True

        # Tenter le CNN d'abord
        if self._load_cnn():
            return True

        # Fallback sur le MLP classique
        print_info(f"[{self.model_name}] CNN non disponible, fallback sur MLP")
        return super().load()

    def _load_cnn(self) -> bool:
        """Charge le modèle CNN et sa configuration."""
        import tensorflow as tf

        cnn_model_path = config.CNN_MODEL_PATH
        cnn_config_path = config.CNN_CONFIG_PATH

        if not cnn_model_path.exists():
            return False
        if not cnn_config_path.exists():
            print_warning(f"[{self.model_name}] CNN model trouvé mais config manquante: {cnn_config_path}")
            return False

        try:
            # Charger la config
            with open(cnn_config_path, 'r') as f:
                self._cnn_config = json.load(f)

            # Charger le modèle
            self.model = tf.keras.models.load_model(str(cnn_model_path))

            self._use_cnn = True
            self._is_loaded = True

            print_success(
                f"[{self.model_name}] CNN chargé "
                f"(F1={self._cnn_config.get('cv_f1_mean', '?'):.4f}, "
                f"{self._cnn_config.get('n_samples', '?')} samples)"
            )

            return True

        except Exception as e:
            print_error(f"[{self.model_name}] Erreur chargement CNN: {e}")
            self._use_cnn = False
            return False

    # ==========================================================================
    # PRÉDICTION
    # ==========================================================================

    def predict_file(self, audio_path: str, verbose: bool = False) -> Tuple[str, float, float]:
        """
        Prédit si une voiture dans l'audio est bruyante.

        Utilise le CNN (spectrogramme) ou le MLP (features) selon le modèle chargé.

        Paramètres:
            audio_path (str): Chemin vers le fichier audio
            verbose (bool): Afficher les détails de la prédiction

        Retourne:
            tuple: (label, confiance_pourcentage, probabilité_brute)
        """
        if not os.path.exists(audio_path):
            print_error(f"Fichier non trouvé: {audio_path}")
            raise FileNotFoundError(audio_path)

        if not self.ensure_loaded():
            raise RuntimeError("Impossible de charger le modèle NoisyCarDetector")

        if verbose:
            mode = "CNN/spectrogramme" if self._use_cnn else "MLP/features"
            print_header(f"Détection Voiture Bruyante ({mode})")
            print_info(f"Fichier: {audio_path}")

        if self._use_cnn:
            label, confidence, probability = self._predict_cnn(audio_path, verbose)
        else:
            label, confidence, probability = self._predict_mlp(audio_path, verbose)

        if verbose:
            self._display_result(label, confidence, probability)

        return label, confidence, probability

    def _predict_cnn(self, audio_path: str, verbose: bool = False) -> Tuple[str, float, float]:
        """Prédiction via CNN sur mel-spectrogramme."""
        from shared.audio_utils import load_melspectrogram

        cfg = self._cnn_config
        sr         = cfg.get('sr', 22050)
        duration   = cfg.get('duration', 4.0)
        n_mels     = cfg.get('n_mels', 128)
        n_fft      = cfg.get('n_fft', 2048)
        hop_length = cfg.get('hop_length', 512)
        x_mean     = cfg.get('X_mean', 0.0)
        x_std      = cfg.get('X_std', 1.0)

        if verbose:
            print_info(f"Création mel-spectrogramme ({n_mels} mels, {sr} Hz, {duration}s)")

        mel_db = load_melspectrogram(audio_path, sr, duration, n_mels, n_fft, hop_length)
        if mel_db is None:
            raise ValueError(f"Impossible de traiter l'audio: {audio_path}")

        # Normaliser avec les stats du dataset d'entraînement
        mel_norm = (mel_db - x_mean) / (x_std + 1e-8)

        # Préparer le batch : (1, n_mels, time, 1)
        X = mel_norm[np.newaxis, ..., np.newaxis]

        if verbose:
            print_info(f"Input shape: {X.shape}")

        # Prédire
        prediction = self.model.predict(X, verbose=0)
        probability = float(prediction[0][0])

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
        mode_str = "CNN" if self._use_cnn else "MLP"
        print(f"  {Colors.BOLD}Résultat ({mode_str}):{Colors.END}")

        if label == self.positive_label:
            color = Colors.RED
            emoji = "⚠"
        else:
            color = Colors.GREEN
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
        info["backend"] = "CNN" if self._use_cnn else "MLP"
        if self._use_cnn and self._cnn_config:
            info["cnn_f1"] = self._cnn_config.get("cv_f1_mean")
            info["cnn_samples"] = self._cnn_config.get("n_samples")
            info["input_shape"] = self._cnn_config.get("input_shape")
        return info


# ==============================================================================
# POINT D'ENTRÉE CLI
# ==============================================================================

def main():
    """Point d'entrée en ligne de commande."""
    import sys

    if len(sys.argv) < 2:
        print(f"""
{Colors.BOLD}NoisyCarDetector - Détection de voiture bruyante{Colors.END}

{Colors.CYAN}Usage:{Colors.END}
    python -m models.noisy_car_detector.model <fichier_audio>
    python -m models.noisy_car_detector.model audio.wav

{Colors.YELLOW}ATTENTION:{Colors.END}
    N'utiliser que sur des audios où une voiture a été détectée !
    Pour le pipeline complet, utilisez: python -m pipeline.orchestrator

{Colors.CYAN}Backends:{Colors.END}
    CNN (mel-spectrogrammes) : Utilisé si cnn_noisy_car.h5 est présent
    MLP (features manuelles) : Fallback sinon

{Colors.CYAN}Formats supportés:{Colors.END}
    .wav, .mp3, .flac, .ogg, .m4a
        """)
        sys.exit(1)

    audio_path = sys.argv[1]

    detector = NoisyCarDetector()
    label, confidence, prob = detector.predict_file(audio_path, verbose=True)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}[!]{Colors.END} Annulé")
    except Exception as e:
        print_error(str(e))
        raise
