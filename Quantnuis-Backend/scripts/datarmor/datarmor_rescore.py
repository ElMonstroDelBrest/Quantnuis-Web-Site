#!/usr/bin/env python3
"""
Re-score les segments avec un ensemble de modeles (RF + LR + MLP) sur 225 features.
Beaucoup plus precis que le filtre RF 10 features.

Requiert:
    - segments_features.csv (genere par datarmor_extract_features.py)
    - features_all.csv (les 526 samples originaux, a uploader depuis MSI)

Usage:
    python datarmor_rescore.py
    python datarmor_rescore.py --threshold 0.7 --copy-validated validated_segments/
"""

import os
import sys
import shutil
import warnings
warnings.filterwarnings("ignore")

import numpy as np
import pandas as pd
import argparse
from pathlib import Path

from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.neural_network import MLPClassifier
from sklearn.svm import SVC
from sklearn.model_selection import StratifiedKFold, cross_val_score

DATARMOR_WORK = "/home4/datahome/gdgheras/"


def train_ensemble(features_csv):
    """Entraine un ensemble de modeles sur les donnees originales (seed 50/50)."""

    df = pd.read_csv(features_csv)
    meta = ["nfile", "label", "reliability"]
    feature_cols = [c for c in df.columns if c not in meta]

    X_all = np.nan_to_num(df[feature_cols].values, nan=0.0, posinf=0.0, neginf=0.0)
    y = df["label"].values

    print(f"  Training data: {len(df)} samples ({(y==0).sum()} normal, {(y==1).sum()} bruyant)")
    print(f"  Features: {len(feature_cols)}")

    # Feature selection (top 30 par RF importance)
    n_top = 30
    rf_sel = RandomForestClassifier(n_estimators=200, random_state=42, n_jobs=1)
    rf_sel.fit(X_all, y)
    imp = pd.DataFrame({"f": feature_cols, "s": rf_sel.feature_importances_})
    top_features = imp.sort_values("s", ascending=False).head(n_top)["f"].tolist()

    print(f"  Top {n_top} features selectionnees")
    print(f"  Top 5: {', '.join(top_features[:5])}")

    X = np.nan_to_num(df[top_features].values, nan=0.0, posinf=0.0, neginf=0.0)

    # Seed 50/50
    rng = np.random.RandomState(42)
    noisy_idx = np.where(y == 1)[0]
    normal_idx = np.where(y == 0)[0]
    normal_sample = rng.choice(normal_idx, size=len(noisy_idx), replace=False)
    seed_idx = np.concatenate([noisy_idx, normal_sample])

    X_seed, y_seed = X[seed_idx], y[seed_idx]
    print(f"  Seed 50/50: {len(seed_idx)} samples")

    # Scaler
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X_seed)

    # Ensemble de modeles
    models = {
        "RF": RandomForestClassifier(n_estimators=200, random_state=42, n_jobs=1,
                                     class_weight="balanced"),
        "LR": LogisticRegression(max_iter=1000, random_state=42, class_weight="balanced"),
        "MLP": MLPClassifier(hidden_layer_sizes=(64, 32), max_iter=500, random_state=42),
        "GB": GradientBoostingClassifier(n_estimators=100, random_state=42),
        "SVM": SVC(kernel="rbf", probability=True, random_state=42, class_weight="balanced"),
    }

    # Entrainer + evaluer
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    print(f"\n  Scores 5-fold CV:")
    for name, model in models.items():
        f1 = cross_val_score(model, X_scaled, y_seed, cv=cv, scoring="f1")
        print(f"    {name}: F1={f1.mean():.4f} (+/- {f1.std():.4f})")
        model.fit(X_scaled, y_seed)

    return models, scaler, top_features


def rescore_segments(segments_csv, models, scaler, feature_names):
    """Re-score les segments avec l'ensemble de modeles."""

    df = pd.read_csv(segments_csv)
    print(f"\n  Segments a scorer: {len(df)}")

    # Aligner les features
    missing = [f for f in feature_names if f not in df.columns]
    if missing:
        print(f"  ATTENTION: {len(missing)} features manquantes, mises a 0")
        for f in missing:
            df[f] = 0.0

    X = np.nan_to_num(df[feature_names].values, nan=0.0, posinf=0.0, neginf=0.0)
    X_scaled = scaler.transform(X)

    # Predictions de chaque modele
    probas = {}
    for name, model in models.items():
        probas[name] = model.predict_proba(X_scaled)[:, 1]
        print(f"    {name}: {(probas[name] >= 0.5).sum()} positifs")

    # Moyenne des probas (soft voting)
    proba_mean = np.mean(list(probas.values()), axis=0)

    # Vote majoritaire (hard voting)
    votes = np.sum([p >= 0.5 for p in probas.values()], axis=0)

    # Ajouter au DataFrame
    df["proba_ensemble"] = np.round(proba_mean, 4)
    df["votes"] = votes
    df["n_models"] = len(models)
    for name, p in probas.items():
        df[f"proba_{name}"] = np.round(p, 4)

    return df


def main():
    parser = argparse.ArgumentParser(description="Re-scoring ensemble (225 features)")
    parser.add_argument("--segments", type=str,
                        default=os.path.join(DATARMOR_WORK, "segments_features.csv"),
                        help="CSV des features des segments")
    parser.add_argument("--training", type=str,
                        default=os.path.join(DATARMOR_WORK, "features_all.csv"),
                        help="CSV des 526 samples originaux")
    parser.add_argument("--threshold", type=float, default=0.6,
                        help="Seuil ensemble (defaut: 0.6)")
    parser.add_argument("--min-votes", type=int, default=3,
                        help="Votes minimum pour valider (defaut: 3/5)")
    parser.add_argument("--copy-validated", type=str, default=None,
                        help="Copier les segments valides dans ce dossier")
    parser.add_argument("--segments-dir", type=str,
                        default=os.path.join(DATARMOR_WORK, "segments_bruyants"),
                        help="Dossier des WAV segments")
    parser.add_argument("--output", type=str,
                        default=os.path.join(DATARMOR_WORK, "rescore_results.csv"),
                        help="CSV de sortie")
    args = parser.parse_args()

    print("=" * 70)
    print("  RE-SCORING ENSEMBLE - 5 MODELES x 225 FEATURES")
    print("=" * 70)

    # Verifier fichiers
    if not Path(args.training).exists():
        print(f"ERREUR: {args.training} non trouve")
        print("Uploadez features_all.csv depuis le MSI")
        return 1

    if not Path(args.segments).exists():
        print(f"ERREUR: {args.segments} non trouve")
        print("Lancez d'abord: python datarmor_extract_features.py")
        return 1

    # Entrainer l'ensemble
    print("\n[1/3] Entrainement de l'ensemble...")
    models, scaler, feature_names = train_ensemble(args.training)

    # Re-scorer
    print("\n[2/3] Re-scoring des segments...")
    df = rescore_segments(args.segments, models, scaler, feature_names)

    # Filtrer
    validated = df[(df["proba_ensemble"] >= args.threshold) & (df["votes"] >= args.min_votes)]
    rejected = df[~((df["proba_ensemble"] >= args.threshold) & (df["votes"] >= args.min_votes))]

    print(f"\n[3/3] Filtrage (seuil={args.threshold}, votes>={args.min_votes}/5)")

    n_total = len(df)
    n_validated = len(validated)
    n_rejected = n_total - n_validated

    print(f"\n{'=' * 70}")
    print(f"  RESULTATS")
    print(f"{'=' * 70}")
    print(f"  Total segments:  {n_total}")
    print(f"  VALIDES:         {n_validated} ({n_validated/n_total*100:.1f}%)")
    print(f"  REJETES:         {n_rejected} ({n_rejected/n_total*100:.1f}%)")

    # Stats par nombre de votes
    print(f"\n  Distribution des votes:")
    for v in range(len(models) + 1):
        n = (df["votes"] == v).sum()
        print(f"    {v}/5 votes: {n} segments")

    # Top segments
    validated_sorted = validated.sort_values("proba_ensemble", ascending=False)
    if len(validated_sorted) > 0:
        print(f"\n  Top 20 segments valides:")
        for _, r in validated_sorted.head(20).iterrows():
            print(f"    {r['proba_ensemble']:.3f} ({int(r['votes'])}/5 votes)  {r['nfile']}")

    # Sauvegarder
    df.to_csv(args.output, index=False)
    print(f"\nResultats complets: {args.output}")

    validated_path = args.output.replace(".csv", "_validated.csv")
    validated_sorted.to_csv(validated_path, index=False)
    print(f"Segments valides: {validated_path}")

    # Copier les WAV valides
    if args.copy_validated and len(validated) > 0:
        out_dir = Path(args.copy_validated)
        out_dir.mkdir(parents=True, exist_ok=True)
        seg_dir = Path(args.segments_dir)

        copied = 0
        for _, r in validated_sorted.iterrows():
            src = seg_dir / r["nfile"]
            if src.exists():
                shutil.copy2(str(src), str(out_dir / r["nfile"]))
                copied += 1

        print(f"\nCopie: {copied} WAV dans {out_dir}/")

    print("\nTermine.")


if __name__ == "__main__":
    main()
