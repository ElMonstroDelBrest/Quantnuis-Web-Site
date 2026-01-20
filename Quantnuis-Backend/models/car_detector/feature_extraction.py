#!/usr/bin/env python3
"""
================================================================================
                    EXTRACTION DE FEATURES - DÉTECTION VOITURE
================================================================================

Extraction massive de caractéristiques audio pour la détection de voiture.

Usage:
    python -m models.car_detector.feature_extraction              # Extraire tout
    python -m models.car_detector.feature_extraction status       # Voir statut
    python -m models.car_detector.feature_extraction --force      # Réextraire

================================================================================
"""

import os
import sys
import pandas as pd
from pathlib import Path

from shared import (
    print_header, print_success, print_info, 
    print_warning, print_error, load_audio, 
    normalize_audio, extract_base_features
)
from . import config


def extract_car_features(file_path: str) -> dict | None:
    """
    Extrait les caractéristiques audio pour la détection de voiture.
    
    Utilise la fonction partagée extract_base_features puis peut
    ajouter des features spécifiques à la détection de voiture.
    
    Paramètres:
        file_path (str): Chemin vers le fichier audio
    
    Retourne:
        dict: Dictionnaire des features, ou None si erreur
    """
    try:
        # Charger et normaliser l'audio
        y, sr = load_audio(file_path)
        
        if len(y) == 0:
            return None
        
        y = normalize_audio(y)
        
        # Extraire les features de base
        features = extract_base_features(y, sr)
        
        # Ici on pourrait ajouter des features spécifiques à la détection
        # de voiture si nécessaire (ex: analyse basse fréquence moteur)
        
        return features
        
    except Exception as e:
        print_error(f"Erreur sur {file_path}: {e}")
        return None


def extract_all(target_label: int = None, force: bool = False):
    """
    Extrait les features de tous les slices pour la détection voiture.
    
    Paramètres:
        target_label: Si spécifié, n'extrait que ce label
        force: Si True, réextrait même si déjà fait
    """
    print_header("Extraction Features - Détection Voiture")
    
    # Vérifier que les données existent
    if not config.ANNOTATION_CSV.exists():
        print_error(f"Pas de fichier d'annotations: {config.ANNOTATION_CSV}")
        print_info("Créez d'abord les données avec slice_manager.py")
        return
    
    # Charger les annotations
    df_ann = pd.read_csv(config.ANNOTATION_CSV)
    
    # Charger les features existantes
    df_existing = None
    existing_files = set()
    
    if config.FEATURES_CSV.exists() and not force:
        df_existing = pd.read_csv(config.FEATURES_CSV)
        existing_files = set(df_existing['nfile'].values)
        print_info(f"{len(existing_files)} features déjà extraites")
    
    # Filtrer par label si demandé
    if target_label is not None:
        df_ann = df_ann[df_ann['label'] == target_label]
        print_info(f"Label {target_label}: {len(df_ann)} fichiers")
    else:
        print_info(f"{len(df_ann)} fichiers à traiter")
    
    # Filtrer les déjà traités
    if not force:
        df_to_process = df_ann[~df_ann['nfile'].isin(existing_files)]
        print_info(f"{len(df_to_process)} nouveaux fichiers")
    else:
        df_to_process = df_ann
        print_info(f"Réextraction forcée de {len(df_to_process)} fichiers")
    
    if len(df_to_process) == 0:
        print_success("Tout est déjà extrait")
        return
    
    # Extraction
    new_rows = []
    for i, row in df_to_process.iterrows():
        path = config.SLICES_DIR / row['nfile']
        
        if not path.exists():
            print_warning(f"{row['nfile']} non trouvé")
            continue
        
        features = extract_car_features(str(path))
        
        if features:
            features['nfile'] = row['nfile']
            features['label'] = row['label']
            if 'reliability' in row:
                features['reliability'] = row['reliability']
            new_rows.append(features)
            
            if len(new_rows) % 20 == 0:
                print_info(f"{len(new_rows)} fichiers traités...")
    
    if not new_rows:
        print_warning("Aucune feature extraite")
        return
    
    # Fusionner avec les existants
    df_new = pd.DataFrame(new_rows)
    
    if df_existing is not None and not force:
        df_final = pd.concat([df_existing, df_new], ignore_index=True)
    else:
        df_final = df_new
    
    # Supprimer doublons
    df_final = df_final.drop_duplicates(subset=['nfile'], keep='last')
    
    # Créer le dossier si nécessaire
    config.DATA_DIR.mkdir(parents=True, exist_ok=True)
    
    # Sauvegarder
    df_final.to_csv(config.FEATURES_CSV, index=False)
    
    print_success(f"{len(new_rows)} fichiers extraits")
    print_info(f"Total: {len(df_final)} fichiers avec features")
    print_info(f"Sauvegardé: {config.FEATURES_CSV}")


def show_status():
    """Affiche le statut des features."""
    print_header("Statut Features - Détection Voiture")
    
    if not config.FEATURES_CSV.exists():
        print_error("Pas de fichier de features")
        print_info("Lancez: python -m models.car_detector.feature_extraction")
        return
    
    df = pd.read_csv(config.FEATURES_CSV)
    
    print_info(f"{len(df)} fichiers avec features")
    print_info(f"{len(df.columns) - 3} caractéristiques extraites")
    
    # Distribution par label
    print_header("Distribution")
    for label in sorted(df['label'].unique()):
        count = (df['label'] == label).sum()
        print_info(f"Label {label}: {count}")


def main():
    """Point d'entrée principal."""
    if len(sys.argv) < 2:
        print("\n🚗 EXTRACTION FEATURES - DÉTECTION VOITURE")
        print("=" * 45)
        print("1. Extraire toutes les features")
        print("2. Extraire un label spécifique")
        print("3. Réextraire tout (force)")
        print("4. Voir le statut")
        print("0. Quitter")
        
        choice = input("\nChoix: ").strip()
        
        if choice == "1":
            extract_all()
        elif choice == "2":
            label = input("Label: ").strip()
            extract_all(target_label=int(label))
        elif choice == "3":
            extract_all(force=True)
        elif choice == "4":
            show_status()
    else:
        cmd = sys.argv[1]
        
        if cmd == "status":
            show_status()
        elif cmd == "--label":
            label = int(sys.argv[2]) if len(sys.argv) > 2 else None
            extract_all(target_label=label)
        elif cmd == "--force":
            extract_all(force=True)
        else:
            extract_all()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n⚠ Annulé")
    except Exception as e:
        print_error(str(e))
        raise
