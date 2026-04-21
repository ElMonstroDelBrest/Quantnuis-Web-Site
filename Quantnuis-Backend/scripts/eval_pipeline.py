#!/usr/bin/env python3
"""
Évaluation end-to-end de la pipeline cascade sur les slices annotés.

Usage:
    python -m scripts.eval_pipeline [--n 500] [--seed 42]
"""

import argparse
import random
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import f1_score, classification_report, confusion_matrix

# Ajouter le répertoire racine au path
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from pipeline import Pipeline


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--n", type=int, default=500, help="Nombre de fichiers à tester")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--all", action="store_true", help="Tester tous les fichiers")
    args = parser.parse_args()

    SLICES_DIR = ROOT / "data" / "noisy_car_detector" / "slices"
    ANNOT_PATH = ROOT / "data" / "noisy_car_detector" / "annotation.csv"

    # Chargement annotations
    df = pd.read_csv(ANNOT_PATH)
    df = df[df["nfile"].apply(lambda f: (SLICES_DIR / f).exists())]
    print(f"[i] {len(df)} fichiers annotés disponibles")
    print(f"    Bruyant (1): {(df['label']==1).sum()} | Normal (0): {(df['label']==0).sum()}")

    # Échantillon stratifié
    if not args.all and args.n < len(df):
        random.seed(args.seed)
        bruyants = df[df["label"] == 1].sample(args.n // 2, random_state=args.seed)
        normaux  = df[df["label"] == 0].sample(args.n // 2, random_state=args.seed)
        df_test = pd.concat([bruyants, normaux]).sample(frac=1, random_state=args.seed)
    else:
        df_test = df.sample(frac=1, random_state=args.seed)

    print(f"[i] Évaluation sur {len(df_test)} fichiers ({len(df_test)//2} par classe)\n")

    # Chargement pipeline
    pipeline = Pipeline()
    pipeline.load_models()

    y_true, y_pred = [], []
    car_detected_count = 0
    errors = 0

    for i, (_, row) in enumerate(df_test.iterrows()):
        path = str(SLICES_DIR / row["nfile"])
        try:
            result = pipeline.analyze(path, verbose=False)

            # Vérité terrain : label 1 = bruyant, 0 = normal (tous sont des voitures)
            true_label = int(row["label"])

            # Prédiction pipeline : voiture bruyante = 1, sinon = 0
            pred_label = 1 if (result.car_detected and result.is_noisy) else 0

            y_true.append(true_label)
            y_pred.append(pred_label)

            if result.car_detected:
                car_detected_count += 1

            if (i + 1) % 100 == 0:
                current_f1 = f1_score(y_true, y_pred, zero_division=0)
                print(f"  [{i+1}/{len(df_test)}] F1 courant = {current_f1:.4f} | "
                      f"Cars détectées: {car_detected_count}/{i+1}")

        except Exception as e:
            errors += 1

    # Résultats finaux
    print("\n" + "="*50)
    print("  RÉSULTATS PIPELINE END-TO-END")
    print("="*50)

    f1    = f1_score(y_true, y_pred, pos_label=1)
    f1_0  = f1_score(y_true, y_pred, pos_label=0)
    cm    = confusion_matrix(y_true, y_pred)

    print(f"\n  F1 (bruyant) : {f1:.4f}")
    print(f"  F1 (normal)  : {f1_0:.4f}")
    print(f"  F1 macro     : {(f1+f1_0)/2:.4f}")
    print(f"  Cars détectées par étape 1 : {car_detected_count}/{len(df_test)} "
          f"({100*car_detected_count/len(df_test):.1f}%)")
    print(f"  Erreurs      : {errors}")
    print(f"\n  Matrice de confusion (vrai=lignes, prédit=colonnes):")
    print(f"             Prédit 0  Prédit 1")
    print(f"  Vrai 0  :    {cm[0,0]:5d}     {cm[0,1]:5d}")
    print(f"  Vrai 1  :    {cm[1,0]:5d}     {cm[1,1]:5d}")
    print()
    print(classification_report(y_true, y_pred, target_names=["Normal", "Bruyant"]))


if __name__ == "__main__":
    main()
