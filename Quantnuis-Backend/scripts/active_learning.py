#!/usr/bin/env python3
"""
Active Learning pour NoisyCarDetector.

1. Crée un seed 50/50 (60 bruyant + 60 normal)
2. Entraîne sur le seed
3. Prédit sur le pool restant (uncertainty sampling)
4. Ajoute les samples les plus incertains
5. Répète jusqu'à convergence

Usage:
    python -u scripts/active_learning.py
    python -u scripts/active_learning.py --batch-size 10
    python -u scripts/active_learning.py --max-iters 50
    python -u scripts/active_learning.py --top-features 15
"""

import argparse
import numpy as np
import pandas as pd
from pathlib import Path
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.neural_network import MLPClassifier
from sklearn.model_selection import StratifiedKFold, cross_val_score
from sklearn.metrics import f1_score
import warnings
warnings.filterwarnings("ignore")

DATA_DIR = Path("data/noisy_car_detector")


def load_data(n_features=15):
    """Charge features et sélectionne les meilleures."""
    df = pd.read_csv(DATA_DIR / "features_all.csv")
    meta = ["nfile", "label", "reliability"]
    feature_cols = [c for c in df.columns if c not in meta]

    X_all = df[feature_cols].values
    y = df["label"].values
    nfiles = df["nfile"].values

    # Remplacer NaN
    X_all = np.nan_to_num(X_all, nan=0.0, posinf=0.0, neginf=0.0)

    # Feature selection via RF
    rf = RandomForestClassifier(n_estimators=200, random_state=42, n_jobs=-1)
    rf.fit(X_all, y)
    imp = pd.DataFrame({"f": feature_cols, "s": rf.feature_importances_})
    imp = imp.sort_values("s", ascending=False)
    top = imp.head(n_features)["f"].tolist()

    X = df[top].values
    X = np.nan_to_num(X, nan=0.0, posinf=0.0, neginf=0.0)

    print(f"Data: {len(X)} samples, {n_features} features (from {len(feature_cols)})")
    print(f"Classes: {(y==0).sum()} normal, {(y==1).sum()} bruyant")
    print(f"Top 5 features: {', '.join(top[:5])}")

    return X, y, nfiles, top


def create_seed(y, seed=42):
    """Crée un seed 50/50: tous les bruyants + même nombre de normaux."""
    rng = np.random.RandomState(seed)

    noisy_idx = np.where(y == 1)[0]
    normal_idx = np.where(y == 0)[0]

    # Prendre tous les bruyants + autant de normaux
    n_noisy = len(noisy_idx)
    normal_sample = rng.choice(normal_idx, size=n_noisy, replace=False)

    seed_idx = np.concatenate([noisy_idx, normal_sample])
    pool_idx = np.setdiff1d(normal_idx, normal_sample)

    print(f"\nSeed: {len(seed_idx)} samples ({n_noisy} bruyant + {n_noisy} normal)")
    print(f"Pool: {len(pool_idx)} samples (normal restants)")

    return seed_idx, pool_idx


def evaluate_cv(X, y, model_name="LR"):
    """Évalue en 5-fold CV, retourne F1 moyen."""
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    if model_name == "LR":
        model = LogisticRegression(max_iter=1000, random_state=42, class_weight="balanced")
    elif model_name == "MLP":
        model = MLPClassifier(hidden_layer_sizes=(64, 32), max_iter=500,
                              random_state=42, early_stopping=True)
    else:
        model = LogisticRegression(max_iter=1000, random_state=42, class_weight="balanced")

    n_splits = min(5, min(np.bincount(y.astype(int))))
    if n_splits < 2:
        n_splits = 2

    cv = StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=42)
    scores = cross_val_score(model, X_scaled, y, cv=cv, scoring="f1")
    return scores.mean(), scores.std()


def uncertainty_sampling(X_train, y_train, X_pool, n_select):
    """Sélectionne les samples du pool les plus incertains."""
    scaler = StandardScaler()
    X_train_s = scaler.fit_transform(X_train)
    X_pool_s = scaler.transform(X_pool)

    model = LogisticRegression(max_iter=1000, random_state=42, class_weight="balanced")
    model.fit(X_train_s, y_train)

    # Probabilités sur le pool
    proba = model.predict_proba(X_pool_s)[:, 1]

    # Incertitude = distance à 0.5 (plus c'est petit, plus c'est incertain)
    uncertainty = np.abs(proba - 0.5)

    # Sélectionner les plus incertains
    n_select = min(n_select, len(X_pool))
    selected = np.argsort(uncertainty)[:n_select]

    return selected, proba


def main():
    parser = argparse.ArgumentParser(description="Active Learning NoisyCarDetector")
    parser.add_argument("--batch-size", type=int, default=10, help="Samples ajoutés par itération")
    parser.add_argument("--max-iters", type=int, default=100, help="Max itérations")
    parser.add_argument("--top-features", type=int, default=15, help="Nombre de features")
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    args = parser.parse_args()

    print("=" * 60)
    print("  ACTIVE LEARNING - NoisyCarDetector")
    print("=" * 60)

    # Load data
    X, y, nfiles, feature_names = load_data(args.top_features)

    # Create balanced seed
    train_idx, pool_idx = create_seed(y, seed=args.seed)

    # Track history
    history = []
    best_f1 = 0
    best_iter = 0
    no_improve = 0

    print(f"\nBatch size: {args.batch_size} | Max iters: {args.max_iters}")
    print(f"{'='*60}")
    print(f"{'Iter':>4} | {'Train':>5} | {'N/B':>7} | {'F1 (LR)':>10} | {'F1 (MLP)':>10} | {'Pool':>5}")
    print(f"{'-'*60}")

    for iteration in range(args.max_iters):
        X_train = X[train_idx]
        y_train = y[train_idx]
        X_pool = X[pool_idx]

        n_normal = (y_train == 0).sum()
        n_noisy = (y_train == 1).sum()

        # Evaluate
        f1_lr, std_lr = evaluate_cv(X_train, y_train, "LR")
        f1_mlp, std_mlp = evaluate_cv(X_train, y_train, "MLP")

        f1_best = max(f1_lr, f1_mlp)
        best_model = "LR" if f1_lr >= f1_mlp else "MLP"

        history.append({
            "iter": iteration,
            "n_train": len(train_idx),
            "n_normal": n_normal,
            "n_noisy": n_noisy,
            "f1_lr": f1_lr,
            "f1_mlp": f1_mlp,
            "pool_size": len(pool_idx),
        })

        marker = ""
        if f1_best > best_f1:
            best_f1 = f1_best
            best_iter = iteration
            no_improve = 0
            marker = " *"
        else:
            no_improve += 1

        print(f"{iteration:4d} | {len(train_idx):5d} | {n_normal:3d}/{n_noisy:3d} | "
              f"{f1_lr:.4f}±{std_lr:.3f} | {f1_mlp:.4f}±{std_mlp:.3f} | {len(pool_idx):5d}{marker}")

        # Stop conditions
        if len(pool_idx) == 0:
            print("\nPool épuisé.")
            break

        if no_improve >= 15:
            print(f"\nConvergence (pas d'amélioration depuis 15 itérations)")
            break

        # Select uncertain samples from pool
        selected, proba = uncertainty_sampling(X_train, y_train, X_pool, args.batch_size)

        # Move selected from pool to train
        selected_pool_idx = pool_idx[selected]
        train_idx = np.concatenate([train_idx, selected_pool_idx])
        pool_idx = np.delete(pool_idx, selected)

    # Summary
    print(f"\n{'='*60}")
    print(f"  RÉSUMÉ")
    print(f"{'='*60}")
    print(f"Meilleur F1: {best_f1:.4f} (iter {best_iter})")
    print(f"Dataset final: {len(train_idx)} samples ({(y[train_idx]==0).sum()} N / {(y[train_idx]==1).sum()} B)")
    print(f"Pool restant: {len(pool_idx)} samples")

    # Save history
    hist_df = pd.DataFrame(history)
    hist_path = DATA_DIR / "active_learning_history.csv"
    hist_df.to_csv(hist_path, index=False)
    print(f"\nHistorique: {hist_path}")

    # Save plot
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))

        ax1.plot(hist_df["n_train"], hist_df["f1_lr"], "b-o", markersize=3, label="Logistic Regression")
        ax1.plot(hist_df["n_train"], hist_df["f1_mlp"], "r-s", markersize=3, label="MLP (64,32)")
        ax1.axhline(y=best_f1, color="g", linestyle="--", alpha=0.5, label=f"Best={best_f1:.4f}")
        ax1.set_xlabel("Nombre de samples d'entraînement")
        ax1.set_ylabel("F1 Score (CV)")
        ax1.set_title("Active Learning: F1 vs Taille du dataset")
        ax1.legend()
        ax1.grid(True, alpha=0.3)

        ax2.plot(hist_df["iter"], hist_df["n_normal"], "b-", label="Normal")
        ax2.plot(hist_df["iter"], hist_df["n_noisy"], "r-", label="Bruyant")
        ax2.set_xlabel("Itération")
        ax2.set_ylabel("Nombre de samples")
        ax2.set_title("Évolution du dataset")
        ax2.legend()
        ax2.grid(True, alpha=0.3)

        plt.tight_layout()
        plot_path = DATA_DIR / "active_learning_curve.png"
        plt.savefig(plot_path, dpi=150)
        plt.close()
        print(f"Graphique: {plot_path}")
    except Exception as e:
        print(f"Plot skipped: {e}")


if __name__ == "__main__":
    main()
