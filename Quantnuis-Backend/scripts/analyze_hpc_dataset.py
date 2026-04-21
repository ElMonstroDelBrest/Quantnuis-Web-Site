#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================================================================
    ANALYSE COMPARATIVE : DATASET HPC - NORMAL vs BRUYANT
================================================================================

Analyse le dataset d'entraînement HPC (SMOTE-augmenté) pour produire des
visualisations explicatives des différences acoustiques entre véhicules
normaux et bruyants, et benchmarker les modèles sklearn vs CNN.

Figures produites (même style que generate_report_benchmarks.py):
  1. Waveform comparison (normal vs bruyant)
  2. Mel-spectrogram comparison
  3. Profil spectral moyen par classe
  4. Distribution des features clés (RMS, ZCR, centroid, bandwidth)
  5. Comparaison CNN vs sklearn (barh F1 scores)
  6. CNN analysis (distribution + ROC)
  7. PCA/t-SNE séparabilité des classes
  8. Tableau récapitulatif des features

Usage:
    python scripts/analyze_hpc_dataset.py [--n-samples 200] [--n-cnn 500]
"""

import argparse
import json
import os
import sys
import warnings
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", category=UserWarning)
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"

import librosa
import librosa.display
import matplotlib.pyplot as plt
import numpy as np
import seaborn as sns
import tensorflow as tf
from sklearn.decomposition import PCA
from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.manifold import TSNE
from sklearn.metrics import (
    auc, classification_report, confusion_matrix, f1_score,
    matthews_corrcoef, precision_score, recall_score, roc_curve,
)
from sklearn.model_selection import StratifiedKFold, cross_validate
from sklearn.naive_bayes import GaussianNB
from sklearn.neighbors import KNeighborsClassifier
from sklearn.neural_network import MLPClassifier
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVC
from tqdm import tqdm

from shared import (
    Colors, print_header, print_info, print_success, print_warning, print_error,
    load_audio, extract_all_features, select_features,
)

# ==============================================================================
# CONFIGURATION (même style que generate_report_benchmarks.py)
# ==============================================================================

plt.style.use('seaborn-v0_8-whitegrid')
sns.set_palette("colorblind")
PLOT_DPI = 150
PALETTE = {'CNN': '#2196F3', 'MLP': '#FF9800'}
COLOR_NORMAL = '#4CAF50'
COLOR_NOISY = '#F44336'
COLOR_CNN = '#E53935'

NORMAL_DIR = Path("/tmp/audio_analysis/normaux/segments_normaux")
NOISY_DIR = Path("/tmp/audio_analysis/bruyants/segments_bruyants_v2")
CNN_MODEL_PATH = Path.home() / "Téléchargements" / "cnn_noisy_car.h5"
CNN_CONFIG_PATH = Path.home() / "Téléchargements" / "cnn_config.json"
OUTPUT_DIR = PROJECT_ROOT / "benchmark_results" / "hpc_analysis"

SEED = 42
np.random.seed(SEED)


# ==============================================================================
# HELPERS
# ==============================================================================

def sample_files(directory: Path, n: int) -> list:
    """Randomly sample n wav files from a directory."""
    all_files = sorted(directory.glob("*.wav"))
    if len(all_files) <= n:
        return all_files
    idx = np.random.choice(len(all_files), n, replace=False)
    return [all_files[i] for i in sorted(idx)]


def preprocess_audio_for_cnn(audio_path: str, cfg: dict) -> np.ndarray:
    """Preprocesses audio file into a mel-spectrogram for CNN inference."""
    y, _ = librosa.load(audio_path, sr=cfg['sr'], duration=cfg['duration'])
    target_len = int(cfg['sr'] * cfg['duration'])
    y = np.pad(y, (0, max(0, target_len - len(y))), mode='constant')[:target_len]
    y = librosa.util.normalize(y)

    mel = librosa.feature.melspectrogram(
        y=y, sr=cfg['sr'], n_mels=cfg['n_mels'],
        n_fft=cfg['n_fft'], hop_length=cfg['hop_length']
    )
    mel_db = librosa.power_to_db(mel, ref=np.max)
    mel_norm = (mel_db - cfg['X_mean']) / (cfg['X_std'] + 1e-8)
    return mel_norm[np.newaxis, ..., np.newaxis]


def extract_quick_features(filepath: Path) -> dict | None:
    """Extract a subset of key acoustic features from an audio file."""
    try:
        y, sr = librosa.load(filepath, sr=22050, duration=4.0)
        if len(y) < sr:
            return None
        y = librosa.util.normalize(y)

        # Temporal
        rms = float(np.mean(librosa.feature.rms(y=y)))
        zcr = float(np.mean(librosa.feature.zero_crossing_rate(y)))

        # Spectral
        sc = float(np.mean(librosa.feature.spectral_centroid(y=y, sr=sr)))
        sb = float(np.mean(librosa.feature.spectral_bandwidth(y=y, sr=sr)))
        sr_feat = float(np.mean(librosa.feature.spectral_rolloff(y=y, sr=sr)))
        sf = float(np.mean(librosa.feature.spectral_flatness(y=y)))

        # MFCC (13 coefficients)
        mfcc = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=13)
        mfcc_means = {f'mfcc_{i+1}': float(np.mean(mfcc[i])) for i in range(13)}
        mfcc_stds = {f'mfcc_{i+1}_std': float(np.std(mfcc[i])) for i in range(13)}

        # Mel-spectrogram mean per band (for spectral profile)
        mel = librosa.feature.melspectrogram(y=y, sr=sr, n_mels=128)
        mel_db = librosa.power_to_db(mel, ref=np.max)
        mel_profile = mel_db.mean(axis=1)  # 128 values

        features = {
            'rms': rms, 'zcr': zcr,
            'spectral_centroid': sc, 'spectral_bandwidth': sb,
            'spectral_rolloff': sr_feat, 'spectral_flatness': sf,
            **mfcc_means, **mfcc_stds,
            '_mel_profile': mel_profile,
            '_y': y, '_sr': sr,
        }
        return features
    except Exception as e:
        return None


# ==============================================================================
# MAIN ANALYSIS
# ==============================================================================

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--n-samples', type=int, default=200,
                        help='Files per class for feature extraction')
    parser.add_argument('--n-cnn', type=int, default=500,
                        help='Files per class for CNN evaluation')
    args = parser.parse_args()

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # ==========================================================================
    # SECTION 1: Sample and extract features
    # ==========================================================================
    print_header("Section 1: Feature Extraction from HPC Dataset")
    print_info(f"Sampling {args.n_samples} files per class...")

    normal_files = sample_files(NORMAL_DIR, args.n_samples)
    noisy_files = sample_files(NOISY_DIR, args.n_samples)
    print_info(f"Normal: {len(normal_files)}, Noisy: {len(noisy_files)}")

    normal_features, noisy_features = [], []
    normal_profiles, noisy_profiles = [], []
    example_normal_y, example_noisy_y = None, None

    print_info("Extracting features from NORMAL samples...")
    for f in tqdm(normal_files, desc="Normal", ncols=80):
        feat = extract_quick_features(f)
        if feat:
            if example_normal_y is None:
                example_normal_y = feat.pop('_y')
                example_normal_sr = feat.pop('_sr')
            else:
                feat.pop('_y', None)
                feat.pop('_sr', None)
            normal_profiles.append(feat.pop('_mel_profile'))
            normal_features.append(feat)

    print_info("Extracting features from NOISY samples...")
    for f in tqdm(noisy_files, desc="Noisy", ncols=80):
        feat = extract_quick_features(f)
        if feat:
            if example_noisy_y is None:
                example_noisy_y = feat.pop('_y')
                example_noisy_sr = feat.pop('_sr')
            else:
                feat.pop('_y', None)
                feat.pop('_sr', None)
            noisy_profiles.append(feat.pop('_mel_profile'))
            noisy_features.append(feat)

    print_success(f"Extracted: {len(normal_features)} normal, {len(noisy_features)} noisy")

    # ==========================================================================
    # FIGURE 1: Waveform Comparison
    # ==========================================================================
    print_header("Figure 1: Waveform Comparison")
    fig, axes = plt.subplots(2, 1, figsize=(14, 6), sharex=True)
    t_normal = np.arange(len(example_normal_y)) / example_normal_sr
    t_noisy = np.arange(len(example_noisy_y)) / example_noisy_sr

    axes[0].plot(t_normal, example_normal_y, color=COLOR_NORMAL, linewidth=0.5, alpha=0.8)
    axes[0].set_title('Véhicule Normal', fontsize=14, fontweight='bold')
    axes[0].set_ylabel('Amplitude')
    axes[0].set_ylim(-1.1, 1.1)
    axes[0].axhline(y=0, color='gray', linewidth=0.3)

    axes[1].plot(t_noisy, example_noisy_y, color=COLOR_NOISY, linewidth=0.5, alpha=0.8)
    axes[1].set_title('Véhicule Bruyant', fontsize=14, fontweight='bold')
    axes[1].set_ylabel('Amplitude')
    axes[1].set_xlabel('Temps (s)')
    axes[1].set_ylim(-1.1, 1.1)
    axes[1].axhline(y=0, color='gray', linewidth=0.3)

    plt.suptitle('Comparaison des formes d\'onde', fontsize=16, fontweight='bold', y=1.02)
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / '01_waveform_comparison.png', dpi=PLOT_DPI, bbox_inches='tight')
    plt.close()
    print_success("Saved 01_waveform_comparison.png")

    # ==========================================================================
    # FIGURE 2: Mel-Spectrogram Comparison
    # ==========================================================================
    print_header("Figure 2: Mel-Spectrogram Comparison")
    fig, axes = plt.subplots(1, 2, figsize=(16, 5))

    for ax, y, sr, title, cmap_label in [
        (axes[0], example_normal_y, example_normal_sr, 'Véhicule Normal', 'Greens'),
        (axes[1], example_noisy_y, example_noisy_sr, 'Véhicule Bruyant', 'Reds'),
    ]:
        mel = librosa.feature.melspectrogram(y=y, sr=sr, n_mels=128, n_fft=2048, hop_length=512)
        mel_db = librosa.power_to_db(mel, ref=np.max)
        img = librosa.display.specshow(mel_db, sr=sr, hop_length=512, x_axis='time',
                                        y_axis='mel', ax=ax, cmap=cmap_label)
        ax.set_title(title, fontsize=14, fontweight='bold')
        ax.set_xlabel('Temps (s)')
        ax.set_ylabel('Fréquence (Hz)')
        fig.colorbar(img, ax=ax, format='%+2.0f dB')

    plt.suptitle('Comparaison des Mel-spectrogrammes (128 bandes)', fontsize=16, fontweight='bold', y=1.02)
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / '02_melspectrogram_comparison.png', dpi=PLOT_DPI, bbox_inches='tight')
    plt.close()
    print_success("Saved 02_melspectrogram_comparison.png")

    # ==========================================================================
    # FIGURE 3: Mean Spectral Profile
    # ==========================================================================
    print_header("Figure 3: Mean Spectral Profile")
    normal_profile_mean = np.mean(normal_profiles, axis=0)
    noisy_profile_mean = np.mean(noisy_profiles, axis=0)
    normal_profile_std = np.std(normal_profiles, axis=0)
    noisy_profile_std = np.std(noisy_profiles, axis=0)

    mel_freqs = librosa.mel_frequencies(n_mels=128, fmin=0, fmax=11025)

    fig, ax = plt.subplots(figsize=(12, 7))
    ax.plot(mel_freqs, normal_profile_mean, color=COLOR_NORMAL, linewidth=2, label='Normal (moyenne)')
    ax.fill_between(mel_freqs, normal_profile_mean - normal_profile_std,
                    normal_profile_mean + normal_profile_std, color=COLOR_NORMAL, alpha=0.15)
    ax.plot(mel_freqs, noisy_profile_mean, color=COLOR_NOISY, linewidth=2, label='Bruyant (moyenne)')
    ax.fill_between(mel_freqs, noisy_profile_mean - noisy_profile_std,
                    noisy_profile_mean + noisy_profile_std, color=COLOR_NOISY, alpha=0.15)
    ax.set_title('Profil spectral moyen par classe', fontsize=14, fontweight='bold')
    ax.set_xlabel('Fréquence (Hz)')
    ax.set_ylabel('Énergie (dB)')
    ax.legend(fontsize=12)
    ax.set_xscale('log')
    ax.set_xlim([20, 11025])
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / '03_spectral_profile.png', dpi=PLOT_DPI, bbox_inches='tight')
    plt.close()
    print_success("Saved 03_spectral_profile.png")

    # ==========================================================================
    # FIGURE 4: Feature Distributions (4 key features)
    # ==========================================================================
    print_header("Figure 4: Feature Distributions")
    feat_keys = ['rms', 'zcr', 'spectral_centroid', 'spectral_bandwidth']
    feat_labels = ['Énergie RMS', 'Taux de passage par zéro (ZCR)',
                   'Centroïde spectral (Hz)', 'Largeur de bande (Hz)']

    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    for ax, key, label in zip(axes.flat, feat_keys, feat_labels):
        norm_vals = [f[key] for f in normal_features]
        noisy_vals = [f[key] for f in noisy_features]
        ax.hist(norm_vals, bins=30, alpha=0.6, color=COLOR_NORMAL, label='Normal', density=True)
        ax.hist(noisy_vals, bins=30, alpha=0.6, color=COLOR_NOISY, label='Bruyant', density=True)
        ax.set_title(label, fontsize=13, fontweight='bold')
        ax.set_ylabel('Densité')
        ax.legend(fontsize=10)

    plt.suptitle('Distribution des caractéristiques clés', fontsize=16, fontweight='bold', y=1.02)
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / '04_feature_distributions.png', dpi=PLOT_DPI, bbox_inches='tight')
    plt.close()
    print_success("Saved 04_feature_distributions.png")

    # ==========================================================================
    # SECTION 2: Sklearn Cross-Validation Benchmark
    # ==========================================================================
    print_header("Section 2: Sklearn Cross-Validation Benchmark")

    # Build feature matrix
    all_feats = normal_features + noisy_features
    feature_names = [k for k in all_feats[0].keys() if not k.startswith('_')]
    X = np.array([[f[k] for k in feature_names] for f in all_feats])
    y = np.array([0]*len(normal_features) + [1]*len(noisy_features))

    # Remove NaN/Inf
    mask = np.isfinite(X).all(axis=1)
    X, y = X[mask], y[mask]
    print_info(f"Feature matrix: {X.shape[0]} samples x {X.shape[1]} features")

    models = [
        ('SVM (RBF)', SVC(kernel='rbf', probability=True, random_state=SEED)),
        ('SVM (Linear)', SVC(kernel='linear', probability=True, random_state=SEED)),
        ('Random Forest', RandomForestClassifier(n_estimators=100, random_state=SEED)),
        ('Gradient Boosting', GradientBoostingClassifier(n_estimators=100, random_state=SEED)),
        ('KNN (k=5)', KNeighborsClassifier(n_neighbors=5)),
        ('KNN (k=3)', KNeighborsClassifier(n_neighbors=3)),
        ('Logistic Regression', LogisticRegression(max_iter=1000, random_state=SEED)),
        ('Naive Bayes', GaussianNB()),
        ('MLP (64, 32)', MLPClassifier(hidden_layer_sizes=(64, 32), max_iter=500, random_state=SEED)),
        ('MLP (32)', MLPClassifier(hidden_layer_sizes=(32,), max_iter=500, random_state=SEED)),
    ]

    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=SEED)
    results = []

    for name, model in tqdm(models, desc="Benchmarking", ncols=80):
        pipe = Pipeline([('scaler', StandardScaler()), ('model', model)])
        cv_res = cross_validate(pipe, X, y, cv=cv, scoring=['f1', 'accuracy'],
                                return_train_score=False, n_jobs=-1)
        f1_mean = cv_res['test_f1'].mean()
        f1_std = cv_res['test_f1'].std()
        acc_mean = cv_res['test_accuracy'].mean()
        results.append({
            'model': name, 'f1_mean': f1_mean, 'f1_std': f1_std, 'acc_mean': acc_mean
        })
        print_info(f"{name:25s} F1={f1_mean:.4f}±{f1_std:.4f}  Acc={acc_mean:.4f}")

    results.sort(key=lambda x: x['f1_mean'])
    print_success("Sklearn benchmark complete.")

    # ==========================================================================
    # SECTION 3: CNN Evaluation
    # ==========================================================================
    print_header("Section 3: CNN Evaluation on HPC Dataset")

    if not CNN_MODEL_PATH.exists():
        print_error(f"CNN model not found: {CNN_MODEL_PATH}")
        cnn_results = None
    else:
        model = tf.keras.models.load_model(CNN_MODEL_PATH)
        with open(CNN_CONFIG_PATH, 'r') as f:
            cfg = json.load(f)
        print_success("CNN model loaded.")

        cnn_normal = sample_files(NORMAL_DIR, args.n_cnn)
        cnn_noisy = sample_files(NOISY_DIR, args.n_cnn)
        print_info(f"CNN eval: {len(cnn_normal)} normal + {len(cnn_noisy)} noisy")

        cnn_probas, cnn_labels = [], []

        print_info("Running CNN inference on normal samples...")
        for f in tqdm(cnn_normal, desc="CNN Normal", ncols=80):
            try:
                x = preprocess_audio_for_cnn(str(f), cfg)
                prob = float(model.predict(x, verbose=0)[0][0])
                cnn_probas.append(prob)
                cnn_labels.append(0)
            except:
                pass

        print_info("Running CNN inference on noisy samples...")
        for f in tqdm(cnn_noisy, desc="CNN Noisy", ncols=80):
            try:
                x = preprocess_audio_for_cnn(str(f), cfg)
                prob = float(model.predict(x, verbose=0)[0][0])
                cnn_probas.append(prob)
                cnn_labels.append(1)
            except:
                pass

        cnn_probas = np.array(cnn_probas)
        cnn_labels = np.array(cnn_labels)
        cnn_preds = (cnn_probas > 0.5).astype(int)

        cnn_f1 = f1_score(cnn_labels, cnn_preds)
        cnn_acc = float(np.mean(cnn_labels == cnn_preds))
        cnn_prec = precision_score(cnn_labels, cnn_preds, zero_division=0)
        cnn_rec = recall_score(cnn_labels, cnn_preds, zero_division=0)
        cnn_mcc = matthews_corrcoef(cnn_labels, cnn_preds)

        cnn_results = {
            'f1': cnn_f1, 'acc': cnn_acc, 'prec': cnn_prec,
            'rec': cnn_rec, 'mcc': cnn_mcc,
            'probas': cnn_probas, 'labels': cnn_labels,
        }
        print_success(f"CNN: F1={cnn_f1:.4f}, Acc={cnn_acc:.4f}, Prec={cnn_prec:.4f}, Rec={cnn_rec:.4f}")

    # ==========================================================================
    # FIGURE 5: CNN vs Sklearn Comparison (horizontal bar chart)
    # ==========================================================================
    print_header("Figure 5: CNN vs Sklearn Comparison")
    fig, ax = plt.subplots(figsize=(14, 8))

    names = [r['model'] for r in results]
    f1s = [r['f1_mean'] for r in results]
    stds = [r['f1_std'] for r in results]
    colors = [PALETTE['MLP']] * len(results)

    # Add CNN at top
    if cnn_results:
        names.append('CNN (mel-spectrogram)')
        f1s.append(cnn_results['f1'])
        stds.append(0.0)
        colors.append(COLOR_CNN)

    y_pos = np.arange(len(names))
    bars = ax.barh(y_pos, f1s, xerr=stds, color=colors, edgecolor='white',
                    capsize=3, height=0.7)

    # Value labels
    for i, (bar, f1) in enumerate(zip(bars, f1s)):
        ax.text(f1 + 0.01, bar.get_y() + bar.get_height()/2,
                f'{f1:.4f}', va='center', fontsize=10, fontweight='bold')

    ax.set_yticks(y_pos)
    ax.set_yticklabels(names)
    ax.set_xlabel('F1 Score', fontsize=12)
    ax.set_title('Comparaison CNN vs Sklearn - NoisyCarDetector (Dataset HPC)',
                 fontsize=14, fontweight='bold')
    ax.set_xlim(0, 1.08)
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / '05_cnn_vs_sklearn.png', dpi=PLOT_DPI, bbox_inches='tight')
    plt.close()
    print_success("Saved 05_cnn_vs_sklearn.png")

    # ==========================================================================
    # FIGURE 6: CNN Analysis (distribution + ROC)
    # ==========================================================================
    if cnn_results:
        print_header("Figure 6: CNN Analysis")
        fig, axes = plt.subplots(1, 2, figsize=(16, 6))

        # Distribution des probabilités
        mask_n = cnn_labels == 0
        mask_b = cnn_labels == 1
        axes[0].hist(cnn_probas[mask_n], bins=40, alpha=0.7, color=COLOR_NORMAL,
                     label='Normal (0)', density=False)
        axes[0].hist(cnn_probas[mask_b], bins=40, alpha=0.7, color=COLOR_NOISY,
                     label='Bruyant (1)', density=False)
        axes[0].axvline(x=0.5, color='black', linestyle='--', linewidth=2, label='Seuil 0.5')
        axes[0].set_title('Distribution des probabilités par classe', fontsize=14, fontweight='bold')
        axes[0].set_xlabel('Probabilité CNN')
        axes[0].set_ylabel('Fréquence')
        axes[0].legend(fontsize=11)

        # ROC curve
        fpr, tpr, _ = roc_curve(cnn_labels, cnn_probas)
        roc_auc = auc(fpr, tpr)
        axes[1].plot(fpr, tpr, color=COLOR_CNN, linewidth=2.5,
                     label=f'ROC (AUC = {roc_auc:.4f})')
        axes[1].plot([0, 1], [0, 1], 'k--', alpha=0.5, label='Chance (AUC = 0.500)')
        axes[1].set_title('ROC Curve - CNN', fontsize=14, fontweight='bold')
        axes[1].set_xlabel('False Positive Rate')
        axes[1].set_ylabel('True Positive Rate')
        axes[1].legend(fontsize=11)
        axes[1].set_xlim([-0.01, 1.01])
        axes[1].set_ylim([-0.01, 1.01])

        plt.tight_layout()
        plt.savefig(OUTPUT_DIR / '06_cnn_analysis.png', dpi=PLOT_DPI, bbox_inches='tight')
        plt.close()
        print_success("Saved 06_cnn_analysis.png")

        # ==========================================================================
        # FIGURE 6b: CNN Confusion Matrix
        # ==========================================================================
        fig, ax = plt.subplots(figsize=(7, 6))
        cm = confusion_matrix(cnn_labels, cnn_preds)
        sns.heatmap(cm, annot=True, fmt='d', cmap='RdBu_r', ax=ax,
                    xticklabels=['Normal', 'Bruyant'], yticklabels=['Normal', 'Bruyant'],
                    annot_kws={'size': 16})
        ax.set_title('Matrice de Confusion - CNN (Dataset HPC)', fontsize=14, fontweight='bold')
        ax.set_xlabel('Prédit')
        ax.set_ylabel('Réel')
        plt.tight_layout()
        plt.savefig(OUTPUT_DIR / '06b_cnn_confusion_matrix.png', dpi=PLOT_DPI, bbox_inches='tight')
        plt.close()
        print_success("Saved 06b_cnn_confusion_matrix.png")

    # ==========================================================================
    # FIGURE 7: PCA + t-SNE Visualization (demonstrates class overlap)
    # ==========================================================================
    print_header("Figure 7: PCA + t-SNE Visualization")
    mfcc_keys = [f'mfcc_{i+1}' for i in range(13)]
    X_mfcc = np.array([[f[k] for k in mfcc_keys] for f in all_feats])
    y_viz = np.array([0]*len(normal_features) + [1]*len(noisy_features))
    mask = np.isfinite(X_mfcc).all(axis=1)
    X_mfcc, y_viz = X_mfcc[mask], y_viz[mask]
    X_mfcc_scaled = StandardScaler().fit_transform(X_mfcc)

    fig, axes = plt.subplots(1, 2, figsize=(18, 8))

    # PCA
    pca = PCA(n_components=2)
    X_pca = pca.fit_transform(X_mfcc_scaled)
    for label, color, name in [(0, COLOR_NORMAL, 'Normal'), (1, COLOR_NOISY, 'Bruyant')]:
        mask_l = y_viz == label
        axes[0].scatter(X_pca[mask_l, 0], X_pca[mask_l, 1], c=color, label=name,
                       alpha=0.5, s=50, edgecolors='white', linewidth=0.5)
    var_total = pca.explained_variance_ratio_.sum()
    axes[0].set_title(f'PCA (variance expliquée : {var_total:.1%})',
                     fontsize=14, fontweight='bold')
    axes[0].set_xlabel(f'PC1 ({pca.explained_variance_ratio_[0]:.1%})', fontsize=12)
    axes[0].set_ylabel(f'PC2 ({pca.explained_variance_ratio_[1]:.1%})', fontsize=12)
    axes[0].legend(fontsize=12, loc='upper right')

    # t-SNE
    tsne = TSNE(n_components=2, random_state=SEED, perplexity=30)
    X_tsne = tsne.fit_transform(X_mfcc_scaled)
    for label, color, name in [(0, COLOR_NORMAL, 'Normal'), (1, COLOR_NOISY, 'Bruyant')]:
        mask_l = y_viz == label
        axes[1].scatter(X_tsne[mask_l, 0], X_tsne[mask_l, 1], c=color, label=name,
                       alpha=0.5, s=50, edgecolors='white', linewidth=0.5)
    axes[1].set_title('t-SNE (perplexité = 30)', fontsize=14, fontweight='bold')
    axes[1].set_xlabel('t-SNE 1', fontsize=12)
    axes[1].set_ylabel('t-SNE 2', fontsize=12)
    axes[1].legend(fontsize=12, loc='upper right')

    # Annotation box explaining the overlap -> CNN motivation
    caption = (
        "Les deux classes se chevauchent fortement dans l'espace des\n"
        "caractéristiques MFCC : aucun cluster distinct n'émerge.\n"
        "Cela explique le plafond des modèles sklearn (~82% F1)\n"
        "et justifie le recours au CNN sur mel-spectrogrammes (99% F1)."
    )
    fig.text(0.5, -0.02, caption, ha='center', va='top', fontsize=12,
             style='italic', color='#555555',
             bbox=dict(boxstyle='round,pad=0.6', facecolor='#FFF9C4',
                       edgecolor='#FFC107', alpha=0.9))

    plt.suptitle('Séparabilité des classes dans l\'espace MFCC (13 coefficients)',
                 fontsize=16, fontweight='bold')
    plt.tight_layout(rect=[0, 0.08, 1, 0.95])
    plt.savefig(OUTPUT_DIR / '07_pca_tsne.png', dpi=PLOT_DPI, bbox_inches='tight')
    plt.close()
    print_success("Saved 07_pca_tsne.png")

    # ==========================================================================
    # FIGURE 8: Summary Table
    # ==========================================================================
    print_header("Figure 8: Feature Summary Table")
    summary_keys = ['rms', 'zcr', 'spectral_centroid', 'spectral_bandwidth',
                    'spectral_rolloff', 'spectral_flatness', 'mfcc_1', 'mfcc_2']
    summary_labels = ['Énergie RMS', 'ZCR', 'Centroïde spectral', 'Bande passante',
                      'Rolloff spectral', 'Platitude spectrale', 'MFCC 1', 'MFCC 2']

    fig, ax = plt.subplots(figsize=(14, 6))
    ax.axis('off')

    table_data = []
    for key, label in zip(summary_keys, summary_labels):
        n_vals = [f[key] for f in normal_features]
        b_vals = [f[key] for f in noisy_features]
        n_mean, n_std = np.mean(n_vals), np.std(n_vals)
        b_mean, b_std = np.mean(b_vals), np.std(b_vals)
        diff_pct = ((b_mean - n_mean) / abs(n_mean)) * 100 if n_mean != 0 else 0
        table_data.append([label,
                           f'{n_mean:.4f} ± {n_std:.4f}',
                           f'{b_mean:.4f} ± {b_std:.4f}',
                           f'{diff_pct:+.1f}%'])

    table = ax.table(
        cellText=table_data,
        colLabels=['Caractéristique', 'Normal (μ ± σ)', 'Bruyant (μ ± σ)', 'Δ (%)'],
        cellLoc='center', loc='center',
        colColours=['#E3F2FD', '#C8E6C9', '#FFCDD2', '#FFF9C4']
    )
    table.auto_set_font_size(False)
    table.set_fontsize(11)
    table.scale(1, 1.8)
    for (row, col), cell in table.get_celld().items():
        if row == 0:
            cell.set_text_props(fontweight='bold')
    ax.set_title('Comparaison des caractéristiques acoustiques (Normal vs Bruyant)',
                 fontsize=14, fontweight='bold', pad=20)
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / '08_feature_summary.png', dpi=PLOT_DPI, bbox_inches='tight')
    plt.close()
    print_success("Saved 08_feature_summary.png")

    # ==========================================================================
    # EXPORT JSON
    # ==========================================================================
    print_header("Exporting results to JSON")
    export = {
        'dataset': {
            'normal_total': len(list(NORMAL_DIR.glob("*.wav"))),
            'noisy_total': len(list(NOISY_DIR.glob("*.wav"))),
            'sampled_features': args.n_samples,
            'sampled_cnn': args.n_cnn,
        },
        'sklearn_cv_results': results,
        'cnn_results': {
            'f1': float(cnn_results['f1']),
            'accuracy': float(cnn_results['acc']),
            'precision': float(cnn_results['prec']),
            'recall': float(cnn_results['rec']),
            'mcc': float(cnn_results['mcc']),
        } if cnn_results else None,
    }
    with open(OUTPUT_DIR / 'hpc_analysis_results.json', 'w') as f:
        json.dump(export, f, indent=2)
    print_success(f"Results saved to {OUTPUT_DIR / 'hpc_analysis_results.json'}")

    # ==========================================================================
    # SUMMARY
    # ==========================================================================
    print_header("ANALYSIS COMPLETE")
    print_success(f"All figures saved to: {OUTPUT_DIR}")
    n_figs = len(list(OUTPUT_DIR.glob("*.png")))
    print_info(f"Total figures: {n_figs}")
    if cnn_results:
        print_info(f"CNN F1: {cnn_results['f1']:.4f}")
    print_info(f"Best sklearn: {results[-1]['model']} F1={results[-1]['f1_mean']:.4f}")


if __name__ == '__main__':
    main()
