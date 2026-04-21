#!/usr/bin/env python3
"""
Entraîne le RF sur le dataset original (seed 50/50) et exporte le modèle.

Produit: rf_mining_model.pkl (RF + scaler + feature_names)
À uploader sur datarmor pour le script de mining.

Usage:
    python -u scripts/export_rf_model.py
"""

import sys
import pickle
import numpy as np
import pandas as pd
from pathlib import Path
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import StratifiedKFold, cross_val_score
import warnings
warnings.filterwarnings("ignore")

DATA_DIR = Path("data/noisy_car_detector")
OUTPUT = Path("rf_mining_model.pkl")


def main():
    print("=" * 60)
    print("  EXPORT RF MODEL POUR DATARMOR")
    print("=" * 60)

    # Charger features (1192 samples)
    df = pd.read_csv(DATA_DIR / "features_all.csv")
    meta = ["nfile", "label", "reliability"]
    feature_cols = [c for c in df.columns if c not in meta]

    X_all = np.nan_to_num(df[feature_cols].values, nan=0.0, posinf=0.0, neginf=0.0)
    y = df["label"].values

    print(f"Dataset: {len(df)} samples ({(y==0).sum()} normal, {(y==1).sum()} bruyant)")
    print(f"Features: {len(feature_cols)}")

    # Feature selection via RF importance (top 15 pour mining rapide)
    n_features = 15
    rf_sel = RandomForestClassifier(n_estimators=200, random_state=42, n_jobs=-1)
    rf_sel.fit(X_all, y)
    imp = pd.DataFrame({"f": feature_cols, "s": rf_sel.feature_importances_})
    top = imp.sort_values("s", ascending=False).head(n_features)["f"].tolist()

    print(f"\nTop {n_features} features:")
    for i, f in enumerate(top):
        score = imp[imp["f"] == f]["s"].values[0]
        print(f"  {i+1}. {f} ({score:.4f})")

    X = np.nan_to_num(df[top].values, nan=0.0, posinf=0.0, neginf=0.0)

    # Utiliser tout le dataset (equilibre suffisant: 61/39%)
    print(f"\nTraining sur {len(df)} samples complets")

    # Train RF
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    rf = RandomForestClassifier(n_estimators=300, random_state=42, n_jobs=-1, class_weight="balanced")
    rf.fit(X_scaled, y)

    # Validation 5-fold
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    f1_scores = cross_val_score(rf, X_scaled, y, cv=cv, scoring="f1")
    print(f"\n5-fold CV F1: {f1_scores.mean():.4f} (+/- {f1_scores.std():.4f})")

    # Export
    model_data = {
        "rf": rf,
        "scaler": scaler,
        "feature_names": top,
        "n_features": n_features,
        "dataset_size": len(df),
        "f1_cv": float(f1_scores.mean()),
    }

    with open(OUTPUT, "wb") as f:
        pickle.dump(model_data, f)

    print(f"\nModele exporté: {OUTPUT} ({OUTPUT.stat().st_size / 1024:.0f} KB)")
    print("Upload ce fichier sur datarmor avec datarmor_mining.py")


if __name__ == "__main__":
    main()
