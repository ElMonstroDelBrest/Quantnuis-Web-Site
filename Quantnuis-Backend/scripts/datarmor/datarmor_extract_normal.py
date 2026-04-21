#!/usr/bin/env python3
"""
Extrait des segments de voitures normales depuis les resultats de mining.
A lancer APRES datarmor_mining.py.

Lit mining_results.csv et exporte les segments avec proba basse (activite audio
mais pas bruyant = voitures normales probables).

Usage:
    python datarmor_extract_normal.py
    python datarmor_extract_normal.py --max-total 1000 --proba-min 0.05 --proba-max 0.25
"""

import os
os.environ["OMP_NUM_THREADS"] = "1"

import warnings
warnings.filterwarnings("ignore")

import numpy as np
import pandas as pd
import argparse
import soundfile as sf
from pathlib import Path

try:
    import librosa
except ImportError:
    print("ERREUR: pip install librosa")
    exit(1)

SR = 22050
DATARMOR_AUDIO = "/home/datawork-osmose/dataset/QUANTNUIS/"
DATARMOR_WORK = "/home4/datahome/gdgheras/"


def main():
    parser = argparse.ArgumentParser(description="Extraction segments normaux depuis mining_results.csv")
    parser.add_argument("--results", type=str,
                        default=os.path.join(DATARMOR_WORK, "mining_results.csv"),
                        help="CSV des resultats de mining")
    parser.add_argument("--source", type=str, default=DATARMOR_AUDIO,
                        help="Dossier des fichiers WAV source")
    parser.add_argument("--output", type=str,
                        default=os.path.join(DATARMOR_WORK, "segments_normaux"),
                        help="Dossier de sortie")
    parser.add_argument("--proba-min", type=float, default=0.05,
                        help="Proba minimum (exclure silence/vide, defaut: 0.05)")
    parser.add_argument("--proba-max", type=float, default=0.25,
                        help="Proba maximum (clairement pas bruyant, defaut: 0.25)")
    parser.add_argument("--max-total", type=int, default=1000,
                        help="Nombre max de segments a exporter (defaut: 1000)")
    parser.add_argument("--max-per-file", type=int, default=100,
                        help="Max segments par fichier source (defaut: 100)")
    parser.add_argument("--window", type=float, default=4.0,
                        help="Duree fenetre en secondes (defaut: 4.0)")
    args = parser.parse_args()

    print("=" * 70)
    print("  EXTRACTION SEGMENTS NORMAUX")
    print("=" * 70)

    # Charger resultats mining
    if not Path(args.results).exists():
        print(f"ERREUR: {args.results} non trouve")
        print("Lancez d'abord: python datarmor_mining.py")
        return 1

    df = pd.read_csv(args.results)
    print(f"Resultats mining: {len(df)} fenetres")

    # Filtrer: activite audio mais pas bruyant
    normal = df[(df["proba"] >= args.proba_min) & (df["proba"] < args.proba_max)].copy()
    print(f"Segments normaux ({args.proba_min} <= proba < {args.proba_max}): {len(normal)}")

    if len(normal) == 0:
        print("Aucun segment normal trouve. Ajustez les seuils.")
        return 1

    # Equilibrer par fichier source + echantillonner
    rng = np.random.RandomState(42)
    selected = []

    for fname in normal["file"].unique():
        file_segs = normal[normal["file"] == fname]
        n_take = min(len(file_segs), args.max_per_file)
        indices = rng.choice(len(file_segs), size=n_take, replace=False)
        selected.append(file_segs.iloc[indices])

    selected = pd.concat(selected, ignore_index=True)

    # Limiter au total max
    if len(selected) > args.max_total:
        indices = rng.choice(len(selected), size=args.max_total, replace=False)
        selected = selected.iloc[sorted(indices)]

    print(f"Selectionnes: {len(selected)} segments (de {selected['file'].nunique()} fichiers)")
    print(f"Proba range: {selected['proba'].min():.3f} - {selected['proba'].max():.3f}")

    # Exporter les WAV
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    exported = 0
    errors = 0

    for i, (_, row) in enumerate(selected.iterrows(), 1):
        src_path = Path(args.source) / row["file"]
        if not src_path.exists():
            errors += 1
            continue

        try:
            y, _ = librosa.load(str(src_path), sr=SR,
                                offset=row["offset_sec"], duration=args.window)
        except Exception:
            errors += 1
            continue

        if len(y) < SR * 0.5:
            errors += 1
            continue

        fname = Path(row["file"]).stem
        ts = row["timestamp"].replace(":", "")
        out_name = f"{fname}_t{ts}_p{row['proba']:.2f}.wav"
        sf.write(str(output_dir / out_name), y, SR)
        exported += 1

        if i % 100 == 0 or i == len(selected):
            print(f"  [{i}/{len(selected)}] {exported} exportes, {errors} erreurs",
                  flush=True)

    print(f"\n{'=' * 70}")
    print(f"  TERMINE")
    print(f"{'=' * 70}")
    print(f"  Exportes: {exported} segments normaux")
    print(f"  Erreurs: {errors}")
    print(f"  Dossier: {output_dir}/")
    print(f"\n  Ces segments peuvent etre ajoutes au dataset avec label=0")


if __name__ == "__main__":
    main()
