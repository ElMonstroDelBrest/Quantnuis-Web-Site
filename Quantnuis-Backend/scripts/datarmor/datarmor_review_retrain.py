#!/usr/bin/env python3
"""
Active Learning: review top 50 → re-train → re-filter.

Etape 1: Preparer les 50 meilleurs segments pour ecoute
    python datarmor_review_retrain.py --prepare

Etape 2: Annoter dans review/annotations.csv (colonne label: 1=bruyant, 0=normal)

Etape 3: Re-entrainer et re-filtrer
    python datarmor_review_retrain.py --retrain
"""

import os
os.environ["OMP_NUM_THREADS"] = "1"

import sys
import shutil
import warnings
warnings.filterwarnings("ignore")

import numpy as np
import pandas as pd
import argparse
from pathlib import Path

DATARMOR_WORK = "/home4/datahome/gdgheras/"


def prepare_review(n_review=50):
    """Selectionne les top N segments et prepare l'annotation."""

    rescore_path = os.path.join(DATARMOR_WORK, "rescore_results.csv")
    segments_dir = os.path.join(DATARMOR_WORK, "segments_bruyants")
    review_dir = os.path.join(DATARMOR_WORK, "review")

    df = pd.read_csv(rescore_path)

    # Top N par proba ensemble (5/5 votes en priorite)
    top = df.sort_values(["votes", "proba_ensemble"], ascending=[False, False]).head(n_review)

    print(f"Top {n_review} segments selectionnes")
    print(f"  Proba range: {top['proba_ensemble'].min():.3f} - {top['proba_ensemble'].max():.3f}")
    print(f"  Votes: {top['votes'].min()}-{top['votes'].max()}/5")

    # Creer dossier review
    os.makedirs(review_dir, exist_ok=True)

    # Copier les WAV
    copied = 0
    for _, r in top.iterrows():
        src = Path(segments_dir) / r["nfile"]
        if src.exists():
            shutil.copy2(str(src), os.path.join(review_dir, r["nfile"]))
            copied += 1

    print(f"  {copied} fichiers copies dans {review_dir}/")

    # Creer le CSV d'annotation
    annot = top[["nfile", "proba_ensemble", "votes"]].copy()
    annot["label"] = ""  # A remplir: 1=bruyant, 0=normal
    annot_path = os.path.join(review_dir, "annotations.csv")
    annot.to_csv(annot_path, index=False)

    print(f"\n  CSV d'annotation: {annot_path}")
    print(f"  Remplissez la colonne 'label' (1=bruyant, 0=normal)")

    # Generer notebook pour ecoute facile
    nb_path = os.path.join(review_dir, "ecoute.py")
    with open(nb_path, "w") as f:
        f.write("""#!/usr/bin/env python3
# Lancer dans JupyterHub pour ecouter les segments
# Ou copier/coller dans une cellule de notebook

import IPython.display as ipd
import pandas as pd
from pathlib import Path

review_dir = Path("%s")
annot = pd.read_csv(review_dir / "annotations.csv")

for i, row in annot.iterrows():
    wav_path = review_dir / row["nfile"]
    print(f"\\n[{i+1}/{len(annot)}] {row['nfile']}")
    print(f"  Proba: {row['proba_ensemble']:.3f} | Votes: {int(row['votes'])}/5")
    if wav_path.exists():
        ipd.display(ipd.Audio(str(wav_path)))
    print("  Label: 1=bruyant, 0=normal → Remplir dans annotations.csv")
    print("-" * 60)
""" % review_dir)

    print(f"  Script d'ecoute: {nb_path}")
    print(f"\n  INSTRUCTIONS:")
    print(f"  1. Ouvrez un notebook JupyterHub")
    print(f"  2. Copiez le contenu de {nb_path} dans une cellule")
    print(f"  3. Ecoutez chaque segment")
    print(f"  4. Remplissez annotations.csv (label: 1 ou 0)")
    print(f"  5. Lancez: python datarmor_review_retrain.py --retrain")


def retrain_and_rescore():
    """Re-entraine avec les nouvelles annotations et re-filtre tout."""

    from sklearn.preprocessing import StandardScaler
    from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
    from sklearn.linear_model import LogisticRegression
    from sklearn.neural_network import MLPClassifier
    from sklearn.svm import SVC
    from sklearn.model_selection import StratifiedKFold, cross_val_score

    review_dir = os.path.join(DATARMOR_WORK, "review")
    annot_path = os.path.join(review_dir, "annotations.csv")
    features_orig = os.path.join(DATARMOR_WORK, "features_all.csv")
    segments_features = os.path.join(DATARMOR_WORK, "segments_features.csv")

    # Charger annotations
    annot = pd.read_csv(annot_path)
    annot["label"] = pd.to_numeric(annot["label"], errors="coerce")
    annotated = annot.dropna(subset=["label"])
    annotated["label"] = annotated["label"].astype(int)

    n_noisy = (annotated["label"] == 1).sum()
    n_normal = (annotated["label"] == 0).sum()

    print(f"Annotations chargees: {len(annotated)} ({n_noisy} bruyant, {n_normal} normal)")

    if len(annotated) == 0:
        print("ERREUR: aucune annotation trouvee. Remplissez annotations.csv")
        return 1

    # Charger features des segments annotes
    seg_df = pd.read_csv(segments_features)
    annot_features = seg_df[seg_df["nfile"].isin(annotated["nfile"])].copy()

    # Merge les labels
    label_map = dict(zip(annotated["nfile"], annotated["label"]))
    annot_features["label"] = annot_features["nfile"].map(label_map)
    annot_features = annot_features.dropna(subset=["label"])
    annot_features["label"] = annot_features["label"].astype(int)

    print(f"Features trouvees pour {len(annot_features)} segments annotes")

    # Charger donnees originales
    orig_df = pd.read_csv(features_orig)
    print(f"Donnees originales: {len(orig_df)} samples")

    # Combiner
    meta = ["nfile", "label", "reliability"]
    feature_cols = [c for c in orig_df.columns if c not in meta]

    # S'assurer que les colonnes sont alignees
    for c in feature_cols:
        if c not in annot_features.columns:
            annot_features[c] = 0.0

    combined = pd.concat([
        orig_df[["nfile", "label"] + feature_cols],
        annot_features[["nfile", "label"] + feature_cols],
    ], ignore_index=True)

    print(f"\nDataset combine: {len(combined)} samples")
    print(f"  Original: {len(orig_df)} ({(orig_df['label']==1).sum()} bruyant)")
    print(f"  Nouveau:  {len(annot_features)} ({n_noisy} bruyant, {n_normal} normal)")

    X_all = np.nan_to_num(combined[feature_cols].values, nan=0.0, posinf=0.0, neginf=0.0)
    y_all = combined["label"].values

    # Feature selection
    n_top = 30
    rf_sel = RandomForestClassifier(n_estimators=200, random_state=42, n_jobs=1)
    rf_sel.fit(X_all, y_all)
    imp = pd.DataFrame({"f": feature_cols, "s": rf_sel.feature_importances_})
    top_features = imp.sort_values("s", ascending=False).head(n_top)["f"].tolist()

    print(f"\nTop {n_top} features: {', '.join(top_features[:5])}...")

    X = np.nan_to_num(combined[top_features].values, nan=0.0, posinf=0.0, neginf=0.0)
    y = y_all

    # Seed equilibre
    noisy_idx = np.where(y == 1)[0]
    normal_idx = np.where(y == 0)[0]

    # Prendre tous les bruyants + autant de normaux
    n_noisy_total = len(noisy_idx)
    n_normal_sample = min(len(normal_idx), n_noisy_total)
    rng = np.random.RandomState(42)
    normal_sample = rng.choice(normal_idx, size=n_normal_sample, replace=False)
    seed_idx = np.concatenate([noisy_idx, normal_sample])

    X_seed, y_seed = X[seed_idx], y[seed_idx]
    print(f"Seed equilibre: {len(seed_idx)} ({(y_seed==1).sum()} bruyant, {(y_seed==0).sum()} normal)")

    # Scaler
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X_seed)

    # Entrainer ensemble
    models = {
        "RF": RandomForestClassifier(n_estimators=200, random_state=42, n_jobs=1,
                                     class_weight="balanced"),
        "LR": LogisticRegression(max_iter=1000, random_state=42, class_weight="balanced"),
        "MLP": MLPClassifier(hidden_layer_sizes=(64, 32), max_iter=500, random_state=42),
        "GB": GradientBoostingClassifier(n_estimators=100, random_state=42),
        "SVM": SVC(kernel="rbf", probability=True, random_state=42, class_weight="balanced"),
    }

    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    print(f"\nScores 5-fold CV (dataset augmente):")
    for name, model in models.items():
        f1 = cross_val_score(model, X_scaled, y_seed, cv=cv, scoring="f1")
        print(f"  {name}: F1={f1.mean():.4f} (+/- {f1.std():.4f})")
        model.fit(X_scaled, y_seed)

    # Re-scorer tous les segments
    print(f"\nRe-scoring des {len(seg_df)} segments...")

    for c in top_features:
        if c not in seg_df.columns:
            seg_df[c] = 0.0

    X_seg = np.nan_to_num(seg_df[top_features].values, nan=0.0, posinf=0.0, neginf=0.0)
    X_seg_scaled = scaler.transform(X_seg)

    probas = {}
    for name, model in models.items():
        probas[name] = model.predict_proba(X_seg_scaled)[:, 1]

    seg_df["proba_ensemble_v2"] = np.round(np.mean(list(probas.values()), axis=0), 4)
    seg_df["votes_v2"] = np.sum([p >= 0.5 for p in probas.values()], axis=0)

    for name, p in probas.items():
        seg_df[f"proba_{name}_v2"] = np.round(p, 4)

    # Resultats
    for threshold in [0.6, 0.7, 0.8, 0.9]:
        for min_votes in [3, 4, 5]:
            n = ((seg_df["proba_ensemble_v2"] >= threshold) &
                 (seg_df["votes_v2"] >= min_votes)).sum()
            print(f"  seuil={threshold} votes>={min_votes}/5: {n} segments")

    # Sauvegarder
    output = os.path.join(DATARMOR_WORK, "rescore_results_v2.csv")
    seg_df.to_csv(output, index=False)
    print(f"\nResultats V2: {output}")

    # Filtrer strict (5/5 votes + proba >= 0.8)
    strict = seg_df[(seg_df["votes_v2"] == 5) & (seg_df["proba_ensemble_v2"] >= 0.8)]
    strict_sorted = strict.sort_values("proba_ensemble_v2", ascending=False)

    strict_path = os.path.join(DATARMOR_WORK, "rescore_results_v2_strict.csv")
    strict_sorted.to_csv(strict_path, index=False)
    print(f"Strict (5/5 + >=0.8): {len(strict)} segments → {strict_path}")

    # Copier les validates
    validated_dir = os.path.join(DATARMOR_WORK, "validated_v2")
    os.makedirs(validated_dir, exist_ok=True)
    seg_dir = os.path.join(DATARMOR_WORK, "segments_bruyants")

    copied = 0
    for _, r in strict_sorted.iterrows():
        src = Path(seg_dir) / r["nfile"]
        if src.exists():
            shutil.copy2(str(src), os.path.join(validated_dir, r["nfile"]))
            copied += 1

    print(f"Copies: {copied} WAV dans {validated_dir}/")
    print("\nTermine.")


def main():
    parser = argparse.ArgumentParser(description="Active Learning: review → retrain → refilter")
    parser.add_argument("--prepare", action="store_true",
                        help="Preparer les top 50 pour review")
    parser.add_argument("--retrain", action="store_true",
                        help="Re-entrainer apres annotation et re-filtrer")
    parser.add_argument("--n-review", type=int, default=50,
                        help="Nombre de segments a reviewer (defaut: 50)")
    args = parser.parse_args()

    print("=" * 70)
    print("  ACTIVE LEARNING - Review → Retrain → Refilter")
    print("=" * 70)

    if args.prepare:
        prepare_review(args.n_review)
    elif args.retrain:
        retrain_and_rescore()
    else:
        print("Usage:")
        print("  python datarmor_review_retrain.py --prepare      # Etape 1")
        print("  # Annoter review/annotations.csv")
        print("  python datarmor_review_retrain.py --retrain      # Etape 3")


if __name__ == "__main__":
    main()
