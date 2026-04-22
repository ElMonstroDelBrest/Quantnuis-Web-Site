#!/usr/bin/env python3
"""
================================================================================
                    PIPELINE ORCHESTRATEUR
================================================================================

Orchestre les deux modèles IA dans une séquence :

    ┌─────────────────────────────────────────────────────────────────────────┐
    │                        FLUX DU PIPELINE                                 │
    ├─────────────────────────────────────────────────────────────────────────┤
    │                                                                         │
    │   Fichier Audio                                                         │
    │        │                                                                │
    │        ▼                                                                │
    │   ┌─────────────────┐                                                   │
    │   │  CarDetector    │  Modèle 1 : Détecte si voiture présente           │
    │   │  (Détection)    │                                                   │
    │   └────────┬────────┘                                                   │
    │            │                                                            │
    │            ▼                                                            │
    │   Voiture détectée ?                                                    │
    │     │           │                                                       │
    │    NON         OUI                                                      │
    │     │           │                                                       │
    │     ▼           ▼                                                       │
    │   STOP    ┌─────────────────┐                                           │
    │           │ NoisyCarDetector│  Modèle 2 : Analyse si bruyante           │
    │           │ (Bruit)         │                                           │
    │           └────────┬────────┘                                           │
    │                    │                                                    │
    │                    ▼                                                    │
    │               Résultat Final                                            │
    │                                                                         │
    └─────────────────────────────────────────────────────────────────────────┘

Usage:
    from pipeline import Pipeline
    
    pipeline = Pipeline()
    result = pipeline.analyze("audio.wav")
    
    if result.car_detected and result.is_noisy:
        print("Véhicule bruyant détecté")

================================================================================
"""

import os
from dataclasses import dataclass
from typing import Optional, Dict, Any

from config import get_settings
from shared import (
    print_header, print_success, print_info, 
    print_warning, print_error, Colors,
    load_audio, normalize_audio, extract_base_features
)
from models.car_detector import CarDetector
from models.noisy_car_detector import NoisyCarDetector

settings = get_settings()


# ==============================================================================
# STRUCTURE DU RÉSULTAT
# ==============================================================================

@dataclass
class PipelineResult:
    """
    Résultat du pipeline d'analyse.
    
    Contient les résultats des deux modèles et un message récapitulatif.
    
    Attributs:
        # Modèle 1 - Détection voiture
        car_detected: bool - Une voiture a-t-elle été détectée ?
        car_confidence: float - Confiance de la détection (0-100)
        car_probability: float - Probabilité brute (0-1)
        
        # Modèle 2 - Voiture bruyante (None si pas de voiture)
        is_noisy: Optional[bool] - La voiture est-elle bruyante ?
        noisy_confidence: Optional[float] - Confiance de l'analyse
        noisy_probability: Optional[float] - Probabilité brute
        
        # Métadonnées
        estimated_db: Optional[int] - Estimation décibels
        message: str - Message récapitulatif
    """
    # Modèle 1
    car_detected: bool
    car_confidence: float
    car_probability: float
    
    # Modèle 2 (optionnel)
    is_noisy: Optional[bool] = None
    noisy_confidence: Optional[float] = None
    noisy_probability: Optional[float] = None
    
    # Métadonnées
    message: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Convertit le résultat en dictionnaire."""
        return {
            "car_detected": self.car_detected,
            "car_confidence": self.car_confidence,
            "car_probability": self.car_probability,
            "is_noisy": self.is_noisy,
            "noisy_confidence": self.noisy_confidence,
            "noisy_probability": self.noisy_probability,
            "message": self.message
        }
    
    def to_simplified(self) -> Dict[str, Any]:
        """
        Convertit en format simplifié (compatibilité ancienne API).
        
        Retourne le format attendu par le frontend existant.
        """
        # Déterminer si c'est bruyant (voiture détectée ET bruyante)
        has_noisy_vehicle = self.car_detected and (self.is_noisy or False)

        # Confiance à utiliser
        if has_noisy_vehicle:
            confidence = (self.noisy_confidence or 0) / 100.0
        elif self.car_detected:
            confidence = self.car_confidence / 100.0
        else:
            confidence = (100 - self.car_confidence) / 100.0

        return {
            "hasNoisyVehicle": has_noisy_vehicle,
            "carDetected": self.car_detected,
            "confidence": confidence,
            "message": self.message
        }


# ==============================================================================
# PIPELINE PRINCIPAL
# ==============================================================================

class Pipeline:
    """
    Pipeline d'analyse audio avec deux modèles en cascade.
    
    Usage:
        pipeline = Pipeline()
        result = pipeline.analyze("audio.wav")
        
        # Version verbose avec affichage
        result = pipeline.analyze("audio.wav", verbose=True)
    """
    
    def __init__(self):
        """Initialise le pipeline avec les deux modèles."""
        self.car_detector = CarDetector()
        self.noisy_car_detector = NoisyCarDetector()
        self._models_loaded = False
    
    def load_models(self) -> bool:
        """
        Charge les deux modèles.
        
        Retourne:
            bool: True si les deux modèles sont chargés
        """
        if self._models_loaded:
            return True
        
        car_loaded = self.car_detector.load()
        
        # Le modèle noisy_car n'est chargé que si car_detector fonctionne
        noisy_loaded = self.noisy_car_detector.load()
        
        # Pipeline works if at least one model is available
        self._models_loaded = car_loaded or noisy_loaded

        return self._models_loaded
    
    def analyze(self, audio_path: str, verbose: bool = False) -> PipelineResult:
        """
        Analyse un fichier audio avec le pipeline complet.
        
        Paramètres:
            audio_path: Chemin vers le fichier audio
            verbose: Afficher les détails de l'analyse
        
        Retourne:
            PipelineResult: Résultat de l'analyse
        """
        if verbose:
            print_header("Pipeline d'Analyse Audio")
            print_info(f"Fichier: {audio_path}")
        
        # Vérifier que le fichier existe
        if not os.path.exists(audio_path):
            raise FileNotFoundError(f"Fichier non trouvé: {audio_path}")
        
        # Charger les modèles
        if not self.load_models():
            raise RuntimeError("Impossible de charger les modèles")
        
        # ======================================================================
        # ÉTAPE 1 : DÉTECTION VOITURE
        # ======================================================================

        if verbose:
            print_header("Étape 1 - Détection Voiture")

        if self.car_detector.is_loaded:
            car_label, car_confidence, car_prob = self.car_detector.predict_file(
                audio_path, verbose=verbose
            )
            car_detected = (car_label == self.car_detector.positive_label)
        else:
            # Car detector not available — assume car present, skip to noise analysis
            car_detected = True
            car_confidence = 0.0
            car_prob = 0.0
            if verbose:
                print_warning("CarDetector non disponible, passage direct à l'analyse bruit")

        if verbose:
            if car_detected:
                print_success(f"Voiture détectée ({car_confidence:.1f}%)")
            else:
                print_info(f"Pas de voiture ({car_confidence:.1f}%)")

        # Si pas de voiture, on s'arrête là
        if not car_detected:
            message = f"Pas de voiture détectée (confiance: {car_confidence:.1f}%)"

            if verbose:
                print_header("Résultat Final")
                print_info(message)

            return PipelineResult(
                car_detected=False,
                car_confidence=car_confidence,
                car_probability=car_prob,
                message=message
            )
        
        # ======================================================================
        # ÉTAPE 2 : ANALYSE BRUIT (si voiture détectée)
        # ======================================================================
        
        if verbose:
            print_header("Étape 2 - Analyse Bruit")
        
        # Vérifier si le modèle noisy_car est disponible
        if not self.noisy_car_detector.is_loaded:
            message = f"Voiture détectée ({car_confidence:.1f}%), analyse bruit non disponible"
            
            if verbose:
                print_warning("Modèle d'analyse de bruit non disponible")
            
            return PipelineResult(
                car_detected=True,
                car_confidence=car_confidence,
                car_probability=car_prob,
                message=message
            )
        
        noisy_label, noisy_confidence, noisy_prob = self.noisy_car_detector.predict_file(
            audio_path, verbose=verbose
        )

        is_noisy = (noisy_label == self.noisy_car_detector.positive_label)

        # ======================================================================
        # RÉSULTAT FINAL
        # ======================================================================

        if is_noisy:
            message = f"Véhicule bruyant détecté (confiance : {noisy_confidence:.1f}%)"
        else:
            message = f"Véhicule détecté, niveau sonore conforme (confiance : {noisy_confidence:.1f}%)"

        if verbose:
            print_header("Résultat Final")
            self._display_final_result(car_detected, is_noisy,
                                       car_confidence, noisy_confidence)

        return PipelineResult(
            car_detected=True,
            car_confidence=car_confidence,
            car_probability=car_prob,
            is_noisy=is_noisy,
            noisy_confidence=noisy_confidence,
            noisy_probability=noisy_prob,
            message=message
        )

    def _display_final_result(self, car_detected: bool, is_noisy: bool,
                              car_conf: float, noisy_conf: float):
        """Affiche le résultat final de manière visuelle."""
        print()

        if car_detected and is_noisy:
            color = Colors.RED
            emoji = "⚠"
            label = "VOITURE BRUYANTE"
        elif car_detected:
            color = Colors.GREEN
            emoji = "✓"
            label = "VOITURE NORMALE"
        else:
            color = Colors.CYAN
            emoji = "○"
            label = "PAS DE VOITURE"

        print(f"    {color}{Colors.BOLD}┌───────────────────────────────────────┐{Colors.END}")
        print(f"    {color}{Colors.BOLD}│                                       │{Colors.END}")
        print(f"    {color}{Colors.BOLD}│   {emoji}  {label:^28}  {emoji}   │{Colors.END}")
        print(f"    {color}{Colors.BOLD}│                                       │{Colors.END}")

        if car_detected:
            print(f"    {color}{Colors.BOLD}│   Détection voiture: {car_conf:>5.1f}%           │{Colors.END}")
            if is_noisy is not None:
                print(f"    {color}{Colors.BOLD}│   Analyse bruit:     {noisy_conf:>5.1f}%           │{Colors.END}")
        else:
            print(f"    {color}{Colors.BOLD}│   Confiance:         {car_conf:>5.1f}%           │{Colors.END}")

        print(f"    {color}{Colors.BOLD}│                                       │{Colors.END}")
        print(f"    {color}{Colors.BOLD}└───────────────────────────────────────┘{Colors.END}")
        print()


# ==============================================================================
# POINT D'ENTRÉE CLI
# ==============================================================================

def main():
    """Point d'entrée en ligne de commande."""
    import sys
    
    if len(sys.argv) < 2:
        print(f"""
{Colors.BOLD}Pipeline - Analyse Audio Complète{Colors.END}

Analyse un fichier audio avec les deux modèles :
1. Détection de voiture
2. Analyse de bruit (si voiture détectée)

{Colors.CYAN}Usage:{Colors.END}
    python -m pipeline.orchestrator <fichier_audio>
    python -m pipeline.orchestrator audio.wav

{Colors.CYAN}Formats supportés:{Colors.END}
    .wav, .mp3, .flac, .ogg, .m4a
        """)
        sys.exit(1)
    
    audio_path = sys.argv[1]
    
    pipeline = Pipeline()
    result = pipeline.analyze(audio_path, verbose=True)
    
    print()
    print(f"{Colors.DIM}Résultat JSON:{Colors.END}")
    print(result.to_dict())


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}[!]{Colors.END} Annulé")
    except Exception as e:
        print_error(str(e))
        raise
