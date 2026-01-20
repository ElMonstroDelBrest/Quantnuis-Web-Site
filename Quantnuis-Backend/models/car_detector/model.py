#!/usr/bin/env python3
"""
================================================================================
                    MODÈLE - DÉTECTION VOITURE
================================================================================

Classe principale pour la détection de voiture dans un fichier audio.

Usage:
    from models.car_detector import CarDetector
    
    detector = CarDetector()
    detector.load()
    
    label, confidence, prob = detector.predict_file("audio.wav")
    print(f"{label}: {confidence:.1f}%")

================================================================================
"""

import os
from pathlib import Path
from typing import Tuple

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
    
    Usage:
        detector = CarDetector()
        label, confidence, prob = detector.predict_file("audio.wav")
    """
    
    def __init__(self):
        """Initialise le détecteur de voiture."""
        super().__init__("CarDetector")
    
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
    
    # ==========================================================================
    # PRÉDICTION
    # ==========================================================================
    
    def predict_file(self, audio_path: str, verbose: bool = False) -> Tuple[str, float, float]:
        """
        Prédit si un fichier audio contient une voiture.
        
        Paramètres:
            audio_path (str): Chemin vers le fichier audio
            verbose (bool): Afficher les détails de la prédiction
        
        Retourne:
            tuple: (label, confiance_pourcentage, probabilité_brute)
            
            - label: "VOITURE" ou "PAS_VOITURE"
            - confiance: Pourcentage de confiance (0-100)
            - probabilité: Valeur brute sigmoid (0-1)
        """
        if verbose:
            print_header("Détection Voiture")
            print_info(f"Fichier: {audio_path}")
        
        # Vérifier que le fichier existe
        if not os.path.exists(audio_path):
            print_error(f"Fichier non trouvé: {audio_path}")
            raise FileNotFoundError(audio_path)
        
        # Charger le modèle si nécessaire
        if not self.ensure_loaded():
            raise RuntimeError("Impossible de charger le modèle CarDetector")
        
        # Extraire les features
        if verbose:
            print_info("Extraction des features...")
        
        y, sr = load_audio(audio_path)
        y = normalize_audio(y)
        all_features = extract_base_features(y, sr)
        
        # Sélectionner les features attendues
        features = select_features(all_features, self.feature_names)
        
        # Faire la prédiction
        label, confidence, probability = self.predict_features(features)
        
        if verbose:
            self._display_result(label, confidence, probability)
        
        return label, confidence, probability
    
    def _display_result(self, label: str, confidence: float, probability: float):
        """Affiche le résultat de la prédiction."""
        print()
        print(f"  {Colors.BOLD}Résultat:{Colors.END}")
        
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
