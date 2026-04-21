#!/usr/bin/env python3
"""
Extraction de features audio pour la détection de véhicules bruyants.

Usage:
    python -m models.noisy_car_detector.feature_extraction           # Extraction
    python -m models.noisy_car_detector.feature_extraction --force   # Réextraire tout
    python -m models.noisy_car_detector.feature_extraction --status  # Statut
    python -m models.noisy_car_detector.feature_extraction --label 1 # Un seul label
"""

import argparse
import os
import pandas as pd
from concurrent.futures import ProcessPoolExecutor, as_completed

from shared import (
    print_header, print_success, print_info,
    print_warning, print_error, load_audio,
    normalize_audio, extract_all_features
)
from . import config


def extract_features_from_file(file_path: str) -> dict | None:
    """Extrait les features d'un fichier audio."""
    try:
        y, sr = load_audio(file_path)
        if len(y) == 0:
            return None
        y = normalize_audio(y)
        return extract_all_features(y, sr)
    except Exception as e:
        print_error(f"Erreur: {file_path}: {e}")
        return None


def extract(label: int = None, force: bool = False):
    """Extrait les features de tous les slices."""
    print_header("Extraction Features - NoisyCarDetector")

    if not config.ANNOTATION_CSV.exists():
        print_error(f"Fichier manquant: {config.ANNOTATION_CSV}")
        return 1

    df_ann = pd.read_csv(config.ANNOTATION_CSV)

    # Charger existants
    df_existing = None
    existing_files = set()

    if config.FEATURES_CSV.exists() and not force:
        df_existing = pd.read_csv(config.FEATURES_CSV)
        existing_files = set(df_existing['nfile'].values)
        print_info(f"{len(existing_files)} features existantes")

    # Filtrer par label
    if label is not None:
        df_ann = df_ann[df_ann['label'] == label]
        print_info(f"Label {label}: {len(df_ann)} fichiers")

    # Filtrer déjà traités
    if force:
        df_to_process = df_ann
        print_info(f"Réextraction: {len(df_to_process)} fichiers")
    else:
        df_to_process = df_ann[~df_ann['nfile'].isin(existing_files)]
        print_info(f"Nouveaux: {len(df_to_process)} fichiers")

    if len(df_to_process) == 0:
        print_success("Tout est extrait")
        return 0

    # Extraction parallèle
    new_rows = []
    total = len(df_to_process)
    workers = min(os.cpu_count() or 4, total)
    print_info(f"Extraction parallèle: {workers} workers")

    # Préparer les tâches
    tasks = []
    for _, row in df_to_process.iterrows():
        path = config.SLICES_DIR / row['nfile']
        if not path.exists():
            print_warning(f"Non trouvé: {row['nfile']}")
            continue
        tasks.append((str(path), row['nfile'], int(row['label']),
                       float(row.get('reliability', 0.0))))

    done = 0
    with ProcessPoolExecutor(max_workers=workers) as executor:
        futures = {
            executor.submit(extract_features_from_file, t[0]): t
            for t in tasks
        }
        for future in as_completed(futures):
            path, nfile, lbl, rel = futures[future]
            features = future.result()
            done += 1
            if features:
                features['nfile'] = nfile
                features['label'] = lbl
                features['reliability'] = rel
                new_rows.append(features)
            if done % 50 == 0 or done == len(tasks):
                print_info(f"Progression: {done}/{len(tasks)} ({100*done//len(tasks)}%)")

    if not new_rows:
        print_warning("Aucune feature extraite")
        return 1

    # Fusionner
    df_new = pd.DataFrame(new_rows)

    if df_existing is not None and not force:
        df_final = pd.concat([df_existing, df_new], ignore_index=True)
    else:
        df_final = df_new

    df_final = df_final.drop_duplicates(subset=['nfile'], keep='last')
    config.DATA_DIR.mkdir(parents=True, exist_ok=True)
    df_final.to_csv(config.FEATURES_CSV, index=False)

    print_success(f"Extrait: {len(new_rows)} fichiers")
    print_info(f"Total: {len(df_final)} | Features: {len(df_final.columns) - 3}")
    return 0


def status():
    """Affiche le statut des features."""
    print_header("Statut - NoisyCarDetector")

    if not config.FEATURES_CSV.exists():
        print_error("Pas de features extraites")
        return 1

    df = pd.read_csv(config.FEATURES_CSV)

    print_info(f"Fichiers: {len(df)}")
    print_info(f"Features: {len(df.columns) - 3}")

    for lbl in sorted(df['label'].unique()):
        name = config.NEGATIVE_LABEL if lbl == 0 else config.POSITIVE_LABEL
        print_info(f"  Label {lbl} ({name}): {(df['label'] == lbl).sum()}")

    return 0


def main():
    parser = argparse.ArgumentParser(
        description="Extraction de features pour NoisyCarDetector",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument('--force', '-f', action='store_true',
                        help="Réextraire toutes les features")
    parser.add_argument('--label', '-l', type=int, choices=[0, 1],
                        help="Extraire uniquement ce label")
    parser.add_argument('--status', '-s', action='store_true',
                        help="Afficher le statut")

    args = parser.parse_args()

    if args.status:
        return status()

    return extract(label=args.label, force=args.force)


if __name__ == "__main__":
    try:
        exit(main())
    except KeyboardInterrupt:
        print("\nAnnulé")
        exit(130)
