#!/usr/bin/env python3
"""
================================================================================
    QUANTNUIS — RAPPORT D'ÉVALUATION DE LA PIPELINE
================================================================================

Génère un rapport complet avec graphiques sur les performances de la pipeline.

Graphiques produits:
  1. Matrice de confusion — CarDetector
  2. Matrice de confusion — NoisyCarDetector
  3. Distribution des probabilités par classe (CarDetector)
  4. Distribution des probabilités par classe (NoisyCarDetector)
  5. Courbes ROC — CarDetector & NoisyCarDetector
  6. Latences par cas (boxplot + histogram)
  7. Résumé des précisions par cas
  8. Heatmap des résultats de la cascade

Usage:
    cd Quantnuis-Backend
    python -m scripts.report_pipeline
    python -m scripts.report_pipeline --n 100 --out reports/
    python -m scripts.report_pipeline --n 50 --min-reliability 2
================================================================================
"""

import argparse
import time
import json
import datetime
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.colors import LinearSegmentedColormap

from shared import print_header, print_success, print_info, print_warning, print_error, Colors
from pipeline.orchestrator import Pipeline
from models.car_detector import config as car_cfg
from models.noisy_car_detector import config as noisy_cfg
from scripts.test_pipeline import sample_files


# ==============================================================================
# CONSTANTES
# ==============================================================================

CASE_NOISY  = "Voitures bruyantes"
CASE_NORMAL = "Voitures normales"
CASE_NOISE  = "Bruit / pas voiture"
CASE_CAR    = "Voitures (car_det)"

PALETTE = {
    "car_pos": "#2196F3",
    "car_neg": "#FF9800",
    "noisy":   "#F44336",
    "normal":  "#4CAF50",
    "bg":      "#1a1a2e",
    "grid":    "#2d2d44",
    "text":    "#e0e0e0",
    "accent":  "#7c4dff",
}

CASE_COLORS = {
    CASE_NOISY:  PALETTE["noisy"],
    CASE_NORMAL: PALETTE["normal"],
    CASE_NOISE:  PALETTE["car_neg"],
    CASE_CAR:    PALETTE["car_pos"],
}

plt.rcParams.update({
    "figure.facecolor":  PALETTE["bg"],
    "axes.facecolor":    PALETTE["bg"],
    "axes.edgecolor":    PALETTE["grid"],
    "axes.labelcolor":   PALETTE["text"],
    "xtick.color":       PALETTE["text"],
    "ytick.color":       PALETTE["text"],
    "text.color":        PALETTE["text"],
    "grid.color":        PALETTE["grid"],
    "grid.alpha":        0.6,
    "font.family":       "DejaVu Sans",
    "font.size":         10,
    "axes.titlesize":    13,
    "axes.labelsize":    11,
})


# ==============================================================================
# COLLECTE DES DONNÉES
# ==============================================================================


def collect_results(pipeline, files, case_name, expected_car, expected_noisy, verbose=False):
    """Exécute l'inférence et retourne un DataFrame avec toutes les prédictions."""
    rows = []
    for path in files:
        try:
            t0 = time.time()
            r = pipeline.analyze(path, verbose=False)
            elapsed = time.time() - t0
            rows.append({
                "file":           Path(path).name,
                "case":           case_name,
                "expected_car":   expected_car,
                "expected_noisy": expected_noisy,
                "pred_car":       r.car_detected,
                "car_prob":       r.car_probability,
                "pred_noisy":     r.is_noisy,
                "noisy_prob":     r.noisy_probability,
                "latency":        elapsed,
                "error":          False,
            })
        except Exception as e:
            rows.append({
                "file":           Path(path).name,
                "case":           case_name,
                "expected_car":   expected_car,
                "expected_noisy": expected_noisy,
                "pred_car":       None,
                "car_prob":       None,
                "pred_noisy":     None,
                "noisy_prob":     None,
                "latency":        None,
                "error":          True,
            })
            if verbose:
                print_warning(f"  ERREUR {Path(path).name}: {e}")

    return pd.DataFrame(rows)


def run_inference(n=50, min_reliability=2, verbose=False):
    """Lance l'inférence sur les 4 cas et retourne un DataFrame global."""
    print_header("Chargement des modèles")
    pipeline = Pipeline()
    pipeline.load_models()
    backend = "CRNN" if pipeline.car_detector.use_crnn else "MLP"
    print_success(f"Modèles chargés — CarDetector: {backend}")
    print()

    cases = [
        {"name": CASE_NOISY,  "annotation": noisy_cfg.ANNOTATION_CSV, "slices": noisy_cfg.SLICES_DIR,
         "label": 1, "expected_car": True,  "expected_noisy": True},
        {"name": CASE_NORMAL, "annotation": noisy_cfg.ANNOTATION_CSV, "slices": noisy_cfg.SLICES_DIR,
         "label": 0, "expected_car": True,  "expected_noisy": False},
        {"name": CASE_NOISE,  "annotation": car_cfg.ANNOTATION_CSV,   "slices": car_cfg.SLICES_DIR,
         "label": 0, "expected_car": False, "expected_noisy": None},
        {"name": CASE_CAR,    "annotation": car_cfg.ANNOTATION_CSV,   "slices": car_cfg.SLICES_DIR,
         "label": 1, "expected_car": True,  "expected_noisy": None},
    ]

    dfs = []
    for c in cases:
        print_info(f"Cas : {c['name']} (n={n})")
        files = sample_files(c["annotation"], c["slices"], c["label"],
                             n=n, min_reliability=min_reliability)
        if not files:
            print_warning("  Aucun fichier — cas ignoré")
            continue

        df = collect_results(pipeline, files, c["name"],
                             c["expected_car"], c["expected_noisy"], verbose)
        ok = (df["pred_car"] == df["expected_car"]).mean() * 100
        print_success(f"  car_acc={ok:.1f}%  ({len(df)} fichiers)")
        dfs.append(df)
        print()

    return pd.concat(dfs, ignore_index=True)


# ==============================================================================
# GRAPHIQUES
# ==============================================================================

def _save(fig, out_dir, name):
    """Applique tight_layout, sauvegarde et ferme la figure."""
    fig.tight_layout()
    path = out_dir / name
    fig.savefig(path, dpi=150, bbox_inches="tight",
                facecolor=PALETTE["bg"], edgecolor="none")
    plt.close(fig)
    print_success(f"  Sauvegardé → {path}")
    return path


def plot_confusion_matrix(y_true, y_pred, title, labels, out_dir, fname):
    """Matrice de confusion stylisée."""
    from sklearn.metrics import confusion_matrix

    cm = confusion_matrix(y_true, y_pred)
    cm_pct = cm.astype(float) / cm.sum(axis=1, keepdims=True) * 100

    fig, ax = plt.subplots(figsize=(5, 4))
    fig.suptitle(title, fontsize=14, fontweight="bold", color=PALETTE["text"], y=1.02)

    cmap = LinearSegmentedColormap.from_list(
        "quantnuis", [PALETTE["bg"], PALETTE["accent"]], N=256)
    im = ax.imshow(cm_pct, cmap=cmap, vmin=0, vmax=100)

    ax.set_xticks([0, 1]); ax.set_yticks([0, 1])
    ax.set_xticklabels(labels, fontsize=11)
    ax.set_yticklabels(labels, fontsize=11)
    ax.set_xlabel("Prédit", fontsize=12)
    ax.set_ylabel("Réel", fontsize=12)

    for i in range(2):
        for j in range(2):
            pct = cm_pct[i, j]
            color = "white" if pct < 50 else "black"
            ax.text(j, i, f"{cm[i,j]}\n({pct:.1f}%)",
                    ha="center", va="center",
                    fontsize=12, fontweight="bold", color=color)

    cbar = fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    cbar.ax.yaxis.set_tick_params(color=PALETTE["text"])
    cbar.set_label("%", color=PALETTE["text"])

    return _save(fig, out_dir, fname)


def plot_prob_distribution(df_cases, out_dir, fname):
    """Distributions des probabilités pour CarDetector et NoisyCarDetector."""
    fig, axes = plt.subplots(1, 2, figsize=(13, 5))
    fig.suptitle("Distribution des probabilités", fontsize=15,
                 fontweight="bold", color=PALETTE["text"])

    # CarDetector
    ax = axes[0]
    ax.set_title("CarDetector — P(voiture)", pad=10)
    for case, color in CASE_COLORS.items():
        sub = df_cases[df_cases["case"] == case]["car_prob"].dropna()
        if len(sub) == 0:
            continue
        ax.hist(sub, bins=20, range=(0, 1), alpha=0.65,
                color=color, label=case, edgecolor="none", density=True)
    ax.axvline(0.5, color="white", linewidth=1.5, linestyle="--", alpha=0.7, label="Seuil 0.5")
    ax.set_xlabel("P(voiture)"); ax.set_ylabel("Densité")
    ax.legend(fontsize=8, framealpha=0.3)
    ax.grid(axis="y", alpha=0.4)

    # NoisyCarDetector
    ax = axes[1]
    ax.set_title("NoisyCarDetector — P(bruyant)", pad=10)
    noisy_cases = {CASE_NOISY: PALETTE["noisy"], CASE_NORMAL: PALETTE["normal"]}
    for case, color in noisy_cases.items():
        sub = df_cases[(df_cases["case"] == case) & df_cases["pred_car"]]["noisy_prob"].dropna()
        if len(sub) == 0:
            continue
        ax.hist(sub, bins=20, range=(0, 1), alpha=0.65,
                color=color, label=case, edgecolor="none", density=True)
    ax.axvline(0.5, color="white", linewidth=1.5, linestyle="--", alpha=0.7, label="Seuil 0.5")
    ax.set_xlabel("P(bruyant)"); ax.set_ylabel("Densité")
    ax.legend(fontsize=9, framealpha=0.3)
    ax.grid(axis="y", alpha=0.4)

    return _save(fig, out_dir, fname)


def _plot_roc_subplot(ax, y_true, y_score, title, color):
    """Dessine une courbe ROC sur un axe existant."""
    from sklearn.metrics import roc_curve, auc

    ax.set_title(title)
    if len(y_true) >= 10 and y_true.nunique() >= 2:
        fpr, tpr, _ = roc_curve(y_true, y_score)
        roc_auc = auc(fpr, tpr)
        ax.plot(fpr, tpr, color=color, lw=2.5, label=f"AUC = {roc_auc:.3f}")
        ax.fill_between(fpr, tpr, alpha=0.15, color=color)
    else:
        ax.text(0.5, 0.5, "Données insuffisantes", ha="center", va="center",
                color=PALETTE["text"], fontsize=12)
    ax.plot([0, 1], [0, 1], "--", color=PALETTE["grid"], lw=1.5, alpha=0.8)
    ax.set_xlabel("Taux faux positifs (FPR)")
    ax.set_ylabel("Taux vrais positifs (TPR)")
    ax.legend(fontsize=11, framealpha=0.3)
    ax.grid(alpha=0.3)


def plot_roc_curves(df, out_dir, fname):
    """Courbes ROC pour les deux modèles."""
    fig, axes = plt.subplots(1, 2, figsize=(12, 5))
    fig.suptitle("Courbes ROC", fontsize=15, fontweight="bold", color=PALETTE["text"])

    sub1 = df[df["car_prob"].notna()].copy()
    _plot_roc_subplot(axes[0], sub1["expected_car"].astype(int),
                      sub1["car_prob"], "CarDetector", PALETTE["car_pos"])

    sub2 = df[df["expected_noisy"].notna() & df["noisy_prob"].notna() & df["pred_car"]].copy()
    _plot_roc_subplot(axes[1], sub2["expected_noisy"].astype(int) if len(sub2) else pd.Series(dtype=int),
                      sub2["noisy_prob"] if len(sub2) else pd.Series(dtype=float),
                      "NoisyCarDetector", PALETTE["noisy"])

    return _save(fig, out_dir, fname)


def plot_latency(df, out_dir, fname):
    """Latences par cas — boxplot + histogram."""
    df_lat = df[df["latency"].notna()].copy()
    cases = list(df_lat["case"].unique())
    colors = [CASE_COLORS.get(c, PALETTE["accent"]) for c in cases]

    # Pre-compute per-case groups once
    grouped = {c: df_lat[df_lat["case"] == c]["latency"] for c in cases}

    fig, axes = plt.subplots(1, 2, figsize=(13, 5))
    fig.suptitle("Latences d'inférence", fontsize=15,
                 fontweight="bold", color=PALETTE["text"])

    # Boxplot
    ax = axes[0]
    ax.set_title("Distribution par cas")
    bp = ax.boxplot([grouped[c].values for c in cases], patch_artist=True,
                    medianprops=dict(color="white", linewidth=2))
    for patch, color in zip(bp["boxes"], colors):
        patch.set_facecolor(color); patch.set_alpha(0.7)
    for elem in ["whiskers", "caps", "fliers"]:
        for line in bp[elem]:
            line.set_color(PALETTE["text"]); line.set_alpha(0.6)
    ax.set_xticklabels([c.replace(" ", "\n") for c in cases], fontsize=9)
    ax.set_ylabel("Latence (s)")
    ax.grid(axis="y", alpha=0.4)
    for i, (case, color) in enumerate(zip(cases, colors)):
        mean = grouped[case].mean()
        ax.text(i + 1, mean + 0.002, f"moy\n{mean:.3f}s",
                ha="center", va="bottom", fontsize=8, color=color)

    # Histogram global
    ax = axes[1]
    ax.set_title("Distribution globale")
    all_lat = df_lat["latency"]
    ax.hist(all_lat, bins=30, color=PALETTE["accent"], alpha=0.8, edgecolor="none", density=True)
    mean_lat, p95_lat = all_lat.mean(), all_lat.quantile(0.95)
    ax.axvline(mean_lat, color="white", linewidth=1.5, linestyle="--",
               label=f"Moy: {mean_lat:.3f}s")
    ax.axvline(p95_lat, color=PALETTE["noisy"], linewidth=1.5, linestyle=":",
               label=f"P95: {p95_lat:.3f}s")
    ax.set_xlabel("Latence (s)"); ax.set_ylabel("Densité")
    ax.legend(fontsize=10, framealpha=0.3)
    ax.grid(axis="y", alpha=0.4)

    return _save(fig, out_dir, fname)


def plot_accuracy_bars(df, out_dir, fname):
    """Barres de précision par cas."""
    cases = list(df["case"].unique())
    car_accs, noisy_accs, ns = [], [], []

    for case in cases:
        sub = df[df["case"] == case]
        car_accs.append((sub["pred_car"] == sub["expected_car"]).mean() * 100)
        ns.append(len(sub))
        sub_noisy = sub[sub["expected_noisy"].notna() & sub["pred_car"]]
        noisy_accs.append(
            (sub_noisy["pred_noisy"] == sub_noisy["expected_noisy"]).mean() * 100
            if len(sub_noisy) > 0 else float("nan")
        )

    x = np.arange(len(cases))
    width = 0.35

    fig, ax = plt.subplots(figsize=(10, 5))
    fig.suptitle("Précision par cas", fontsize=15, fontweight="bold", color=PALETTE["text"])

    bars1 = ax.bar(x - width/2, car_accs, width, label="CarDetector",
                   color=PALETTE["car_pos"], alpha=0.85, edgecolor="none")
    bars2 = ax.bar(x + width/2, [v if not np.isnan(v) else 0 for v in noisy_accs],
                   width, label="NoisyCarDetector",
                   color=PALETTE["noisy"], alpha=0.85, edgecolor="none")

    for bar, val in zip(bars1, car_accs):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.5,
                f"{val:.1f}%", ha="center", va="bottom", fontsize=10,
                fontweight="bold", color=PALETTE["car_pos"])
    for bar, val in zip(bars2, noisy_accs):
        if not np.isnan(val):
            ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.5,
                    f"{val:.1f}%", ha="center", va="bottom", fontsize=10,
                    fontweight="bold", color=PALETTE["noisy"])
        else:
            ax.text(bar.get_x() + bar.get_width()/2, 2,
                    "N/A", ha="center", va="bottom", fontsize=9,
                    color=PALETTE["text"], alpha=0.5)
    for i, (n, _) in enumerate(zip(ns, cases)):
        ax.text(i, -6, f"n={n}", ha="center", va="top", fontsize=9,
                color=PALETTE["text"], alpha=0.7)

    ax.axhline(80, color="white", linewidth=1, linestyle="--", alpha=0.4, label="Objectif 80%")
    ax.axhline(100, color=PALETTE["grid"], linewidth=0.5, alpha=0.3)
    ax.set_ylim(-10, 108)
    ax.set_xticks(x)
    ax.set_xticklabels([c.replace(" / ", "\n") for c in cases], fontsize=10)
    ax.set_ylabel("Précision (%)")
    ax.legend(fontsize=10, framealpha=0.3)
    ax.grid(axis="y", alpha=0.3)

    return _save(fig, out_dir, fname)


def plot_cascade_heatmap(df, out_dir, fname):
    """Heatmap de la cascade : résultats détaillés par catégorie d'outcome."""
    # Vectorized computation — no row-wise apply()
    exp_car  = df["expected_car"].fillna(False)
    pred_car = df["pred_car"].fillna(False)
    exp_noisy  = df["expected_noisy"]
    pred_noisy = df["pred_noisy"].fillna(False)

    counts_vec = {
        "Bruit\n→ Bruit\n(TN car)":          (~exp_car & ~pred_car).sum(),
        "Bruit\n→ Voiture\n(FP car)":         (~exp_car & pred_car).sum(),
        "Voiture\n→ Bruit\n(FN car)":         (exp_car & ~pred_car).sum(),
        "Voiture\n→ Voiture\n(TP car)":       (exp_car & pred_car & exp_noisy.isna()).sum(),
        "Bruyante\n→ Normale\n(FN noisy)":    ((exp_noisy == True) & pred_car & ~pred_noisy).sum(),
        "Normale\n→ Bruyante\n(FP noisy)":    ((exp_noisy == False) & pred_car & pred_noisy).sum(),
        "Bruyante\n→ Bruyante\n(TP noisy)":   ((exp_noisy == True) & pred_car & pred_noisy).sum(),
        "Normale\n→ Normale\n(TN noisy)":     ((exp_noisy == False) & pred_car & ~pred_noisy).sum(),
    }

    labels = list(counts_vec.keys())
    values = list(counts_vec.values())
    total = sum(values)
    good_idx = {0, 3, 6, 7}
    colors = ["#4CAF50" if i in good_idx else "#F44336" for i in range(len(labels))]

    fig, ax = plt.subplots(figsize=(13, 5))
    fig.suptitle("Cascade Pipeline — Résultats détaillés", fontsize=15,
                 fontweight="bold", color=PALETTE["text"])

    bars = ax.bar(range(len(labels)), values, color=colors, alpha=0.8, edgecolor="none")
    for bar, val in zip(bars, values):
        pct = val / total * 100 if total > 0 else 0
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.3,
                f"{val}\n({pct:.1f}%)", ha="center", va="bottom",
                fontsize=9, fontweight="bold")

    ax.set_xticks(range(len(labels)))
    ax.set_xticklabels(labels, fontsize=8.5)
    ax.set_ylabel("Nombre de fichiers")
    ax.grid(axis="y", alpha=0.3)
    ax.legend(handles=[
        mpatches.Patch(color="#4CAF50", alpha=0.8, label="Prédiction correcte"),
        mpatches.Patch(color="#F44336", alpha=0.8, label="Erreur"),
    ], fontsize=10, framealpha=0.3)

    return _save(fig, out_dir, fname)


def plot_confidence_by_correctness(df, out_dir, fname):
    """Probabilités selon si la prédiction est correcte ou non."""
    fig, axes = plt.subplots(1, 2, figsize=(13, 5))
    fig.suptitle("Calibration : Probabilité selon le résultat",
                 fontsize=15, fontweight="bold", color=PALETTE["text"])

    # CarDetector
    ax = axes[0]
    ax.set_title("CarDetector")
    correct   = df[df["pred_car"] == df["expected_car"]]["car_prob"].dropna()
    incorrect = df[df["pred_car"] != df["expected_car"]]["car_prob"].dropna()
    ax.hist(correct,   bins=20, range=(0,1), alpha=0.7, color=PALETTE["normal"],
            label=f"Correct ({len(correct)})", density=True)
    ax.hist(incorrect, bins=20, range=(0,1), alpha=0.7, color=PALETTE["noisy"],
            label=f"Incorrect ({len(incorrect)})", density=True)
    ax.axvline(0.5, color="white", linewidth=1.5, linestyle="--", alpha=0.7)
    ax.set_xlabel("P(voiture)"); ax.set_ylabel("Densité")
    ax.legend(fontsize=9, framealpha=0.3); ax.grid(axis="y", alpha=0.4)

    # NoisyCarDetector
    ax = axes[1]
    ax.set_title("NoisyCarDetector")
    sub = df[df["expected_noisy"].notna() & df["pred_car"] & df["noisy_prob"].notna()].copy()
    correct2   = sub[sub["pred_noisy"] == sub["expected_noisy"]]["noisy_prob"].dropna()
    incorrect2 = sub[sub["pred_noisy"] != sub["expected_noisy"]]["noisy_prob"].dropna()
    if len(correct2) > 0:
        ax.hist(correct2,   bins=20, range=(0,1), alpha=0.7, color=PALETTE["normal"],
                label=f"Correct ({len(correct2)})", density=True)
    if len(incorrect2) > 0:
        ax.hist(incorrect2, bins=20, range=(0,1), alpha=0.7, color=PALETTE["noisy"],
                label=f"Incorrect ({len(incorrect2)})", density=True)
    ax.axvline(0.5, color="white", linewidth=1.5, linestyle="--", alpha=0.7)
    ax.set_xlabel("P(bruyant)"); ax.set_ylabel("Densité")
    ax.legend(fontsize=9, framealpha=0.3); ax.grid(axis="y", alpha=0.4)

    return _save(fig, out_dir, fname)


def generate_all_graphs(df, out_dir):
    """Génère tous les graphiques et retourne la liste des fichiers."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    print_header("Génération des graphiques")
    saved = []

    car_rows = df[df["pred_car"].notna() & df["expected_car"].notna()]
    saved.append(plot_confusion_matrix(
        car_rows["expected_car"].astype(int), car_rows["pred_car"].astype(int),
        "Matrice de Confusion — CarDetector", ["Pas voiture", "Voiture"],
        out_dir, "01_confusion_car.png"
    ))

    noisy_rows = df[df["expected_noisy"].notna() & df["pred_noisy"].notna() & df["pred_car"]]
    if len(noisy_rows) >= 4:
        saved.append(plot_confusion_matrix(
            noisy_rows["expected_noisy"].astype(int), noisy_rows["pred_noisy"].astype(int),
            "Matrice de Confusion — NoisyCarDetector", ["Normale", "Bruyante"],
            out_dir, "02_confusion_noisy.png"
        ))

    saved.append(plot_prob_distribution(df, out_dir, "03_prob_distribution.png"))
    saved.append(plot_roc_curves(df, out_dir, "04_roc_curves.png"))
    saved.append(plot_latency(df, out_dir, "05_latency.png"))
    saved.append(plot_accuracy_bars(df, out_dir, "06_accuracy_bars.png"))
    saved.append(plot_cascade_heatmap(df, out_dir, "07_cascade_heatmap.png"))
    saved.append(plot_confidence_by_correctness(df, out_dir, "08_calibration.png"))

    return saved


# ==============================================================================
# RAPPORT JSON + CONSOLE
# ==============================================================================

def build_report(df):
    """Construit le rapport de métriques."""
    from sklearn.metrics import precision_score, recall_score, f1_score, roc_auc_score

    report = {
        "generated_at": datetime.datetime.now().isoformat(),
        "n_total":  int(len(df)),
        "n_errors": int(df["error"].sum()),
    }

    def _clf_metrics(y_true, y_pred, y_score):
        return {
            "n":         int(len(y_true)),
            "accuracy":  float((y_true == y_pred).mean()),
            "precision": float(precision_score(y_true, y_pred, zero_division=0)),
            "recall":    float(recall_score(y_true, y_pred, zero_division=0)),
            "f1":        float(f1_score(y_true, y_pred, zero_division=0)),
            "roc_auc":   float(roc_auc_score(y_true, y_score))
                         if y_true.nunique() >= 2 else None,
        }

    car = df[df["pred_car"].notna() & df["expected_car"].notna()].copy()
    if len(car) > 0:
        report["car_detector"] = _clf_metrics(
            car["expected_car"].astype(int),
            car["pred_car"].astype(int),
            car["car_prob"].fillna(0.5),
        )

    noisy = df[df["expected_noisy"].notna() & df["pred_noisy"].notna() & df["pred_car"]].copy()
    if len(noisy) > 0:
        report["noisy_car_detector"] = _clf_metrics(
            noisy["expected_noisy"].astype(int),
            noisy["pred_noisy"].astype(int),
            noisy["noisy_prob"].fillna(0.5),
        )

    lat = df["latency"].dropna()
    if len(lat) > 0:
        report["latency"] = {
            "mean":   float(lat.mean()),
            "median": float(lat.median()),
            "p95":    float(lat.quantile(0.95)),
            "p99":    float(lat.quantile(0.99)),
            "min":    float(lat.min()),
            "max":    float(lat.max()),
        }

    # By case — single groupby pass
    report["by_case"] = {}
    for case, sub in df.groupby("case"):
        sub_noisy = sub[sub["expected_noisy"].notna() & sub["pred_car"] & sub["pred_noisy"].notna()]
        noisy_acc = (sub_noisy["pred_noisy"] == sub_noisy["expected_noisy"]).mean() \
                    if len(sub_noisy) > 0 else None
        report["by_case"][case] = {
            "n":             int(len(sub)),
            "car_accuracy":  float((sub["pred_car"] == sub["expected_car"]).mean()),
            "noisy_accuracy": float(noisy_acc) if noisy_acc is not None else None,
            "avg_latency":   float(sub["latency"].mean()) if sub["latency"].notna().any() else None,
        }

    car_acc   = report.get("car_detector", {}).get("accuracy", 0)
    noisy_acc = report.get("noisy_car_detector", {}).get("accuracy", 0)
    if car_acc >= 0.90 and noisy_acc >= 0.85:
        verdict = "EXCELLENTE — Prête pour production"
    elif car_acc >= 0.80 and noisy_acc >= 0.75:
        verdict = "BONNE — Prête pour déploiement"
    elif car_acc >= 0.70:
        verdict = "ACCEPTABLE — Amélioration recommandée"
    else:
        verdict = "INSUFFISANTE — Retraining nécessaire"
    report["verdict"] = verdict

    return report


def print_report(report):
    """Affiche le rapport dans le terminal."""
    print_header("RAPPORT D'ÉVALUATION — PIPELINE QUANTNUIS")
    print()

    cd  = report.get("car_detector", {})
    nd  = report.get("noisy_car_detector", {})
    lat = report.get("latency", {})

    print(f"  {'Métrique':<25} {'CarDetector':>15} {'NoisyCarDetector':>17}")
    print(f"  {'-'*60}")
    for metric in ["accuracy", "precision", "recall", "f1", "roc_auc"]:
        v1, v2 = cd.get(metric), nd.get(metric)
        s1 = f"{v1*100:.2f}%" if v1 is not None else "N/A"
        s2 = f"{v2*100:.2f}%" if v2 is not None else "N/A"
        c1 = Colors.GREEN if (v1 or 0) >= 0.85 else (Colors.YELLOW if (v1 or 0) >= 0.70 else Colors.RED)
        c2 = Colors.GREEN if (v2 or 0) >= 0.85 else (Colors.YELLOW if (v2 or 0) >= 0.70 else Colors.RED)
        print(f"  {metric:<25} {c1}{s1:>15}{Colors.END} {c2}{s2:>17}{Colors.END}")
    print(f"  {'n_fichiers':<25} {cd.get('n', 'N/A'):>15} {nd.get('n', 'N/A'):>17}")

    print()
    if lat:
        print("  Latences:")
        print(f"    Moyenne:  {lat['mean']*1000:.1f} ms")
        print(f"    Médiane:  {lat['median']*1000:.1f} ms")
        print(f"    P95:      {lat['p95']*1000:.1f} ms")
        print(f"    P99:      {lat['p99']*1000:.1f} ms")

    print()
    print_header("Par cas")
    print(f"  {'Cas':<26} {'N':>4}  {'Car':>8}  {'Noisy':>8}  {'Latence':>8}")
    print(f"  {'-'*60}")
    for case, c in report.get("by_case", {}).items():
        car_s   = f"{c['car_accuracy']*100:.1f}%"  if c["car_accuracy"]   is not None else "N/A"
        noisy_s = f"{c['noisy_accuracy']*100:.1f}%" if c["noisy_accuracy"] is not None else "N/A"
        lat_s   = f"{c['avg_latency']*1000:.0f}ms"  if c["avg_latency"]    else "N/A"
        color   = Colors.GREEN if (c["car_accuracy"] or 0) >= 0.85 else Colors.YELLOW
        print(f"  {case:<26} {c['n']:>4}  {color}{car_s:>8}{Colors.END}  {noisy_s:>8}  {lat_s:>8}")

    print()
    verdict = report.get("verdict", "")
    if "EXCELLENTE" in verdict or "BONNE" in verdict:
        print_success(f"Verdict: {verdict}")
    elif "ACCEPTABLE" in verdict:
        print_warning(f"Verdict: {verdict}")
    else:
        print_error(f"Verdict: {verdict}")


# ==============================================================================
# MAIN
# ==============================================================================

def main():
    parser = argparse.ArgumentParser(description="Rapport d'évaluation pipeline Quantnuis")
    parser.add_argument("--n", type=int, default=50, help="Fichiers par classe (défaut: 50)")
    parser.add_argument("--min-reliability", type=int, default=2, help="Fiabilité minimale (défaut: 2)")
    parser.add_argument("--out", type=str, default=None, help="Dossier de sortie")
    parser.add_argument("--verbose", "-v", action="store_true")
    args = parser.parse_args()

    if args.out:
        out_dir = Path(args.out)
    else:
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        out_dir = Path("reports") / ts
    out_dir.mkdir(parents=True, exist_ok=True)

    print_header(f"Quantnuis — Rapport Pipeline  (n={args.n} / cas)")
    print_info(f"Sortie : {out_dir.resolve()}")
    print()

    df = run_inference(n=args.n, min_reliability=args.min_reliability, verbose=args.verbose)

    csv_path = out_dir / "raw_results.csv"
    df.to_csv(csv_path, index=False)
    print_success(f"  CSV brut → {csv_path}")
    print()

    saved_graphs = generate_all_graphs(df, out_dir)
    print()

    report = build_report(df)
    print_report(report)

    json_path = out_dir / "metrics.json"
    with open(json_path, "w") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    print()
    print_success(f"Métriques JSON → {json_path}")
    print_success(f"Graphiques ({len(saved_graphs)}) → {out_dir}/")
    print()
    print(f"  {Colors.BOLD}Rapport complet : {out_dir.resolve()}/{Colors.END}")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}[!]{Colors.END} Annulé")
    except Exception as e:
        print_error(str(e))
        raise
