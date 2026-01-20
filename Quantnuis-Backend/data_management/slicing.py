#!/usr/bin/env python3
"""
================================================================================
                    DÉCOUPAGE AUDIO EN SLICES
================================================================================

Découpe un fichier audio long selon un fichier d'annotations CSV.

Format du CSV d'annotations attendu :
    Start,End,Label,Reliability
    00:09:34,00:10:12,1,3
    00:11:30,00:11:43,2,3

Usage:
    python -m data_management.slicing --model car audio.wav annotations.csv
    python -m data_management.slicing --model noisy_car audio.wav annotations.csv

================================================================================
"""

import os
import sys
from pathlib import Path
from datetime import datetime
import pandas as pd
from pydub import AudioSegment

from config import get_settings
from shared import print_header, print_success, print_info, print_warning, print_error

settings = get_settings()


def time_to_seconds(time_str: str) -> int:
    """
    Convertit une chaîne HH:MM:SS en secondes.
    
    Paramètres:
        time_str: Temps au format "HH:MM:SS" ou "MM:SS"
    
    Retourne:
        int: Nombre de secondes
    """
    parts = time_str.split(":")
    
    if len(parts) == 3:  # HH:MM:SS
        return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
    elif len(parts) == 2:  # MM:SS
        return int(parts[0]) * 60 + int(parts[1])
    else:
        raise ValueError(f"Format de temps invalide: {time_str}")


def get_next_slice_num(slices_dir: Path) -> int:
    """Trouve le prochain numéro de slice disponible."""
    if not slices_dir.exists():
        return 1
    
    files = list(slices_dir.glob("slice_*.wav"))
    if not files:
        return 1
    
    nums = [int(f.stem.replace('slice_', '')) for f in files]
    return max(nums) + 1


def slice_audio(
    audio_path: str, 
    annotations_path: str, 
    model_name: str = "car_detector"
):
    """
    Découpe un fichier audio selon les annotations.
    
    Paramètres:
        audio_path: Chemin vers le fichier audio (.wav, .mp3, etc.)
        annotations_path: Chemin vers le CSV d'annotations
        model_name: "car_detector" ou "noisy_car_detector"
    """
    print_header(f"Découpage Audio - {model_name}")
    
    # Charger la config du modèle
    if model_name == "car_detector":
        from models.car_detector import config
    elif model_name == "noisy_car_detector":
        from models.noisy_car_detector import config
    else:
        raise ValueError(f"Modèle inconnu: {model_name}")
    
    slices_dir = config.SLICES_DIR
    annotation_csv = config.ANNOTATION_CSV
    
    # Vérifications
    if not os.path.exists(audio_path):
        print_error(f"Fichier audio non trouvé: {audio_path}")
        return
    
    if not os.path.exists(annotations_path):
        print_error(f"Fichier annotations non trouvé: {annotations_path}")
        return
    
    # Créer les dossiers
    slices_dir.mkdir(parents=True, exist_ok=True)
    config.DATA_DIR.mkdir(parents=True, exist_ok=True)
    
    # Charger les annotations existantes
    df_existing = None
    if annotation_csv.exists():
        df_existing = pd.read_csv(annotation_csv)
        print_info(f"📄 {len(df_existing)} annotations existantes")
    
    # Lire les nouvelles annotations
    df_new = pd.read_csv(annotations_path)
    print_info(f"📥 {len(df_new)} segments à découper")
    
    # Charger l'audio
    print_info(f"🎵 Chargement de {audio_path}...")
    audio = AudioSegment.from_file(audio_path)
    print_info(f"   Durée: {len(audio) / 1000:.1f} secondes")
    
    next_num = get_next_slice_num(slices_dir)
    new_rows = []
    
    for idx, row in df_new.iterrows():
        try:
            start_s = time_to_seconds(row['Start'])
            end_s = time_to_seconds(row['End'])
        except Exception as e:
            print_warning(f"Format de temps invalide ligne {idx}: {e}")
            continue
        
        nfile = f"slice_{next_num:03d}.wav"
        output_path = slices_dir / nfile
        
        if output_path.exists():
            print_warning(f"{nfile} existe déjà, skip")
            continue
        
        try:
            # Découper le segment (pydub travaille en millisecondes)
            segment = audio[start_s * 1000:end_s * 1000]
            segment.export(output_path, format="wav")
            
            new_rows.append({
                'nfile': nfile,
                'length': end_s - start_s,
                'label': row['Label'],
                'reliability': row.get('Reliability', 3)
            })
            
            print_info(f"  ✓ {nfile} ({row['Start']} → {row['End']}, label={row['Label']})")
            next_num += 1
            
        except Exception as e:
            print_error(f"Erreur sur segment {idx}: {e}")
    
    # Fusionner et sauvegarder les annotations
    if new_rows:
        df_add = pd.DataFrame(new_rows)
        
        if df_existing is not None:
            df_final = pd.concat([df_existing, df_add], ignore_index=True)
        else:
            df_final = df_add
        
        df_final = df_final.drop_duplicates(subset=['nfile']).sort_values('nfile')
        df_final.to_csv(annotation_csv, index=False)
        
        print_success(f"{len(new_rows)} slices créés")
        print_info(f"Total: {len(df_final)} annotations")
        print_info(f"Sauvegardé: {annotation_csv}")
    else:
        print_warning("Aucun slice créé")


# ==============================================================================
# POINT D'ENTRÉE CLI
# ==============================================================================

def main():
    """Point d'entrée en ligne de commande."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Découpage audio en slices")
    parser.add_argument(
        "--model", "-m",
        choices=["car", "noisy_car"],
        required=True,
        help="Modèle cible"
    )
    parser.add_argument(
        "audio",
        help="Fichier audio source"
    )
    parser.add_argument(
        "annotations",
        help="Fichier CSV d'annotations"
    )
    
    args = parser.parse_args()
    
    model_map = {
        "car": "car_detector",
        "noisy_car": "noisy_car_detector"
    }
    
    slice_audio(args.audio, args.annotations, model_map[args.model])


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n⚠ Annulé")
    except Exception as e:
        print_error(str(e))
        raise
