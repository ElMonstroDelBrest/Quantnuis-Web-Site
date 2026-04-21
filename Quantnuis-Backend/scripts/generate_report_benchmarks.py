#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================================================================
        COMPLETE BENCHMARK & REPORTING FOR AUDIO CLASSIFICATION MODELS
================================================================================

This script performs a comprehensive evaluation of the pre-trained audio
classification models (NoisyCarDetector and CarDetector) without any retraining.

It covers:
  - Evaluation of CNN and MLP backends for NoisyCarDetector.
  - Cross-validation benchmark for CarDetector using sklearn.
  - Detailed performance metrics (Accuracy, F1, Precision, Recall, MCC, etc.).
  - Inference time profiling (cold/warm starts, step breakdown).
  - Model complexity analysis (parameters, file size).
  - Generation of publication-quality visualizations.
  - Export of all results to a structured JSON file.

Usage:
    python scripts/generate_report_benchmarks.py \
        --output-dir benchmark_results \
        --n-timing-samples 50
"""

import argparse
import io
import json
import os
import sys
import time
import warnings
from contextlib import redirect_stdout
from pathlib import Path

# --- Project root setup (must come before project imports) ---
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# --- Filter warnings for cleaner output ---
warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", category=UserWarning)
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"

# --- Third-party imports ---
import joblib
import librosa
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
import tensorflow as tf
from sklearn.calibration import calibration_curve
from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    auc,
    classification_report,
    confusion_matrix,
    f1_score,
    matthews_corrcoef,
    precision_recall_curve,
    precision_score,
    recall_score,
    roc_curve,
)
from sklearn.model_selection import StratifiedKFold, cross_validate
from sklearn.neural_network import MLPClassifier
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVC
from tqdm import tqdm

# --- Project imports ---
from shared import (
    Colors,
    print_header,
    print_info,
    print_success,
    print_warning,
    print_error,
    load_audio,
    extract_all_features,
    select_features,
)

# ==============================================================================
# CONFIGURATION
# ==============================================================================

# --- Matplotlib professional style setup ---
plt.style.use('seaborn-v0_8-whitegrid')
sns.set_palette("colorblind")
PLOT_DPI = 150
PALETTE = {'CNN': '#2196F3', 'MLP': '#FF9800'}

# --- Path Constants ---
NOISY_CAR_DATA_DIR = PROJECT_ROOT / "data" / "noisy_car_detector"
NOISY_CAR_SLICES_DIR = NOISY_CAR_DATA_DIR / "slices"
NOISY_CAR_ANNOTATION_CSV = NOISY_CAR_DATA_DIR / "annotation.csv"
NOISY_CAR_FEATURES_ALL_CSV = NOISY_CAR_DATA_DIR / "features_all.csv"

CAR_DETECTOR_DATA_DIR = PROJECT_ROOT / "data" / "car_detector"
CAR_DETECTOR_FEATURES_CSV = CAR_DETECTOR_DATA_DIR / "features_all.csv"
CAR_DETECTOR_ANNOTATION_CSV = CAR_DETECTOR_DATA_DIR / "annotation.csv"

NCD_ARTIFACTS = PROJECT_ROOT / "models" / "noisy_car_detector" / "artifacts"
CD_ARTIFACTS = PROJECT_ROOT / "models" / "car_detector" / "artifacts"


# ==============================================================================
# HELPERS
# ==============================================================================

def calculate_metrics(y_true: np.ndarray, y_pred_proba: np.ndarray, threshold: float = 0.5) -> dict:
    """Calculates a comprehensive dictionary of performance metrics."""
    y_pred = (y_pred_proba > threshold).astype(int)

    cm = confusion_matrix(y_true, y_pred)
    tn, fp, fn, tp = cm.ravel()

    return {
        'accuracy': float((tp + tn) / (tp + tn + fp + fn)),
        'precision': float(precision_score(y_true, y_pred, zero_division=0)),
        'recall': float(recall_score(y_true, y_pred, zero_division=0)),
        'f1_score': float(f1_score(y_true, y_pred, zero_division=0)),
        'specificity': float(tn / (tn + fp)) if (tn + fp) > 0 else 0.0,
        'mcc': float(matthews_corrcoef(y_true, y_pred)),
        'report': classification_report(y_true, y_pred, output_dict=True, zero_division=0),
        'confusion_matrix': cm.tolist(),
    }


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


def get_timing_stats(data: list) -> dict:
    """Calculates timing statistics from a list of measurements in seconds."""
    arr = np.array(data) * 1000  # Convert to ms
    return {
        'mean': float(np.mean(arr)),
        'median': float(np.median(arr)),
        'p95': float(np.percentile(arr, 95)),
        'p99': float(np.percentile(arr, 99)),
        'min': float(np.min(arr)),
        'max': float(np.max(arr)),
    }


def get_model_analysis(model, model_path: Path) -> dict:
    """Analyzes a Keras model's complexity."""
    trainable_params = int(np.sum([np.prod(v.shape) for v in model.trainable_weights]))
    non_trainable_params = int(np.sum([np.prod(v.shape) for v in model.non_trainable_weights]))

    with io.StringIO() as s, redirect_stdout(s):
        model.summary()
        summary_str = s.getvalue()

    return {
        'summary': summary_str,
        'total_params': trainable_params + non_trainable_params,
        'trainable_params': trainable_params,
        'non_trainable_params': non_trainable_params,
        'file_size_mb': round(os.path.getsize(model_path) / (1024 * 1024), 3),
    }


# ==============================================================================
# SECTION 1: NoisyCarDetector CNN Evaluation
# ==============================================================================

def evaluate_noisy_car_cnn(output_dir: Path) -> dict | None:
    """Evaluates the NoisyCarDetector CNN model on the full dataset."""
    print_header("Section 1: NoisyCarDetector CNN Evaluation")

    model_path = NCD_ARTIFACTS / "cnn_noisy_car.h5"
    config_path = NCD_ARTIFACTS / "cnn_config.json"
    if not model_path.exists() or not config_path.exists():
        print_error("CNN artifacts not found. Skipping.")
        return None

    model = tf.keras.models.load_model(model_path)
    with open(config_path, 'r') as f:
        cfg = json.load(f)
    print_success("CNN model and config loaded.")

    annotations = pd.read_csv(NOISY_CAR_ANNOTATION_CSV)
    y_true, y_proba = [], []
    skipped = 0

    for _, row in tqdm(annotations.iterrows(), total=len(annotations), desc="CNN Eval"):
        audio_path = NOISY_CAR_SLICES_DIR / row['nfile']
        if not audio_path.exists():
            skipped += 1
            continue

        X = preprocess_audio_for_cnn(str(audio_path), cfg)
        prob = float(model.predict(X, verbose=0)[0][0])

        y_true.append(int(row['label']))
        y_proba.append(prob)

    if skipped > 0:
        print_warning(f"Skipped {skipped} missing audio files.")

    y_true, y_proba = np.array(y_true), np.array(y_proba)
    metrics = calculate_metrics(y_true, y_proba)

    print_info(f"Samples evaluated: {len(y_true)}")
    print_success(f"F1={metrics['f1_score']:.4f}  Acc={metrics['accuracy']:.4f}  MCC={metrics['mcc']:.4f}")
    print_info(f"Classification report:\n{classification_report(y_true, (y_proba > 0.5).astype(int))}")

    return {'metrics': metrics, 'y_true': y_true, 'y_proba': y_proba, 'model': model, 'config': cfg}


# ==============================================================================
# SECTION 2: NoisyCarDetector MLP Evaluation
# ==============================================================================

def evaluate_noisy_car_mlp(output_dir: Path) -> dict | None:
    """Evaluates the NoisyCarDetector MLP model using pre-extracted features."""
    print_header("Section 2: NoisyCarDetector MLP Evaluation")

    model_path = NCD_ARTIFACTS / "model.h5"
    scaler_path = NCD_ARTIFACTS / "scaler.pkl"
    features_path = NCD_ARTIFACTS / "features.txt"

    if not all(p.exists() for p in [model_path, scaler_path, features_path]):
        print_error("MLP artifacts not found. Skipping.")
        return None

    model = tf.keras.models.load_model(model_path)
    scaler = joblib.load(scaler_path)
    with open(features_path, 'r') as f:
        feature_names = [line.strip() for line in f if line.strip()]
    print_success(f"MLP model loaded ({len(feature_names)} features).")

    if not NOISY_CAR_FEATURES_ALL_CSV.exists():
        print_error(f"Features CSV not found: {NOISY_CAR_FEATURES_ALL_CSV}")
        return None

    df = pd.read_csv(NOISY_CAR_FEATURES_ALL_CSV).dropna()

    # Verify all required features exist in CSV
    missing = [f for f in feature_names if f not in df.columns]
    if missing:
        print_error(f"Missing features in CSV: {missing}")
        return None

    X = df[feature_names].values
    y_true = df['label'].values

    X_scaled = scaler.transform(X)
    y_proba = model.predict(X_scaled, verbose=0).flatten()

    metrics = calculate_metrics(y_true, y_proba)

    print_info(f"Samples evaluated: {len(y_true)}")
    print_success(f"F1={metrics['f1_score']:.4f}  Acc={metrics['accuracy']:.4f}  MCC={metrics['mcc']:.4f}")
    print_info(f"Classification report:\n{classification_report(y_true, (y_proba > 0.5).astype(int))}")

    return {'metrics': metrics, 'y_true': y_true, 'y_proba': y_proba, 'model': model}


# ==============================================================================
# SECTION 3: Inference Time Benchmark
# ==============================================================================

def benchmark_inference_time(n_samples: int, cnn_data: dict, mlp_data: dict) -> dict:
    """Benchmarks inference time for both CNN and MLP models."""
    print_header("Section 3: Inference Time Benchmark")

    annotations = pd.read_csv(NOISY_CAR_ANNOTATION_CSV)
    # Sample up to n_samples, but no more than available
    n = min(n_samples, len(annotations))
    sampled = annotations.sample(n=n, random_state=42)
    audio_files = [NOISY_CAR_SLICES_DIR / f for f in sampled['nfile'] if (NOISY_CAR_SLICES_DIR / f).exists()]
    print_info(f"Timing on {len(audio_files)} audio files.")

    cnn_model = cnn_data['model']
    cnn_cfg = cnn_data['config']

    # --- CNN Cold Start ---
    first_file = str(audio_files[0])
    start = time.perf_counter()
    X = preprocess_audio_for_cnn(first_file, cnn_cfg)
    cnn_model.predict(X, verbose=0)
    cnn_cold_start = time.perf_counter() - start

    # --- CNN Warm Runs ---
    cnn_times = {'load': [], 'preprocess': [], 'predict': []}
    for f in tqdm(audio_files, desc="CNN Timing"):
        t0 = time.perf_counter()
        y, _ = librosa.load(str(f), sr=cnn_cfg['sr'], duration=cnn_cfg['duration'])
        t1 = time.perf_counter()

        target_len = int(cnn_cfg['sr'] * cnn_cfg['duration'])
        y = np.pad(y, (0, max(0, target_len - len(y))), mode='constant')[:target_len]
        y = librosa.util.normalize(y)
        mel = librosa.feature.melspectrogram(
            y=y, sr=cnn_cfg['sr'], n_mels=cnn_cfg['n_mels'],
            n_fft=cnn_cfg['n_fft'], hop_length=cnn_cfg['hop_length']
        )
        mel_db = librosa.power_to_db(mel, ref=np.max)
        mel_norm = (mel_db - cnn_cfg['X_mean']) / (cnn_cfg['X_std'] + 1e-8)
        X = mel_norm[np.newaxis, ..., np.newaxis]
        t2 = time.perf_counter()

        cnn_model.predict(X, verbose=0)
        t3 = time.perf_counter()

        cnn_times['load'].append(t1 - t0)
        cnn_times['preprocess'].append(t2 - t1)
        cnn_times['predict'].append(t3 - t2)

    # --- MLP Timing ---
    mlp_model = mlp_data['model']
    scaler = joblib.load(NCD_ARTIFACTS / "scaler.pkl")
    with open(NCD_ARTIFACTS / "features.txt", 'r') as f:
        feature_names = [line.strip() for line in f if line.strip()]

    mlp_times = {'extract': [], 'scale_predict': []}
    for f in tqdm(audio_files, desc="MLP Timing"):
        t0 = time.perf_counter()
        y, sr = load_audio(str(f))
        all_features = extract_all_features(y, sr)
        selected = select_features(all_features, feature_names)
        features = np.array([selected[name] for name in feature_names]).reshape(1, -1)
        t1 = time.perf_counter()

        features_scaled = scaler.transform(features)
        mlp_model.predict(features_scaled, verbose=0)
        t2 = time.perf_counter()

        mlp_times['extract'].append(t1 - t0)
        mlp_times['scale_predict'].append(t2 - t1)

    # --- Calculate stats ---
    cnn_total = np.array(cnn_times['load']) + np.array(cnn_times['preprocess']) + np.array(cnn_times['predict'])
    mlp_total = np.array(mlp_times['extract']) + np.array(mlp_times['scale_predict'])

    # All values in cnn_times/mlp_times/cnn_total/mlp_total are in seconds
    # get_timing_stats converts seconds -> milliseconds internally
    timing_results = {
        'cnn': {
            'cold_start_ms': round(cnn_cold_start * 1000, 2),
            'warm_total_ms': get_timing_stats(list(cnn_total)),
            'breakdown_ms': {
                'load': get_timing_stats(cnn_times['load']),
                'preprocess': get_timing_stats(cnn_times['preprocess']),
                'predict': get_timing_stats(cnn_times['predict']),
            }
        },
        'mlp': {
            'warm_total_ms': get_timing_stats(list(mlp_total)),
            'breakdown_ms': {
                'extract': get_timing_stats(mlp_times['extract']),
                'scale_predict': get_timing_stats(mlp_times['scale_predict']),
            }
        }
    }

    print_info(f"CNN Cold Start: {timing_results['cnn']['cold_start_ms']:.1f} ms")
    print_info(f"CNN Warm Mean:  {timing_results['cnn']['warm_total_ms']['mean']:.1f} ms")
    print_info(f"MLP Warm Mean:  {timing_results['mlp']['warm_total_ms']['mean']:.1f} ms")

    return timing_results


# ==============================================================================
# SECTION 4: Model Complexity Analysis
# ==============================================================================

def analyze_model_complexity(cnn_data: dict, mlp_data: dict) -> dict:
    """Analyzes complexity of CNN and MLP models."""
    print_header("Section 4: Model Complexity Analysis")

    complexity = {
        'cnn': get_model_analysis(cnn_data['model'], NCD_ARTIFACTS / "cnn_noisy_car.h5"),
        'mlp': get_model_analysis(mlp_data['model'], NCD_ARTIFACTS / "model.h5"),
    }

    print_info(f"CNN  | Params: {complexity['cnn']['total_params']:>10,} | Size: {complexity['cnn']['file_size_mb']:.2f} MB")
    print_info(f"MLP  | Params: {complexity['mlp']['total_params']:>10,} | Size: {complexity['mlp']['file_size_mb']:.2f} MB")
    print_info(f"\nCNN Summary:\n{complexity['cnn']['summary']}")
    print_info(f"MLP Summary:\n{complexity['mlp']['summary']}")

    return complexity


# ==============================================================================
# SECTION 5: Visualizations
# ==============================================================================

def generate_visualizations(output_dir: Path, cnn_data: dict, mlp_data: dict, timing_data: dict):
    """Generates all publication-quality visualizations."""
    print_header("Section 5: Generating Visualizations")

    y_true_cnn, y_proba_cnn = cnn_data['y_true'], cnn_data['y_proba']
    y_pred_cnn = (y_proba_cnn > 0.5).astype(int)

    y_true_mlp, y_proba_mlp = mlp_data['y_true'], mlp_data['y_proba']
    y_pred_mlp = (y_proba_mlp > 0.5).astype(int)

    # --- 5a. Confusion Matrices ---
    fig, axes = plt.subplots(1, 2, figsize=(14, 6))
    for ax, y_t, y_p, title, cmap in [
        (axes[0], y_true_cnn, y_pred_cnn, 'CNN Confusion Matrix', 'Blues'),
        (axes[1], y_true_mlp, y_pred_mlp, 'MLP Confusion Matrix', 'Oranges'),
    ]:
        cm = confusion_matrix(y_t, y_p)
        sns.heatmap(cm, annot=True, fmt='d', cmap=cmap, ax=ax,
                    xticklabels=['Normal', 'Noisy'], yticklabels=['Normal', 'Noisy'])
        ax.set_title(title, fontsize=14, fontweight='bold')
        ax.set_xlabel('Predicted')
        ax.set_ylabel('Actual')
    plt.tight_layout()
    plt.savefig(output_dir / 'confusion_matrices.png', dpi=PLOT_DPI, bbox_inches='tight')
    plt.close()
    print_info("Saved confusion_matrices.png")

    # --- 5b. ROC Curve ---
    fig, ax = plt.subplots(figsize=(9, 7))
    for name, y_t, y_p, color in [
        ('CNN', y_true_cnn, y_proba_cnn, PALETTE['CNN']),
        ('MLP', y_true_mlp, y_proba_mlp, PALETTE['MLP']),
    ]:
        fpr, tpr, _ = roc_curve(y_t, y_p)
        roc_auc = auc(fpr, tpr)
        ax.plot(fpr, tpr, label=f'{name} (AUC = {roc_auc:.4f})', color=color, linewidth=2)
    ax.plot([0, 1], [0, 1], 'k--', alpha=0.5, label='Chance (AUC = 0.500)')
    ax.set_title('ROC Curve', fontsize=14, fontweight='bold')
    ax.set_xlabel('False Positive Rate')
    ax.set_ylabel('True Positive Rate')
    ax.legend(fontsize=11)
    ax.set_xlim([-0.01, 1.01])
    ax.set_ylim([-0.01, 1.01])
    plt.tight_layout()
    plt.savefig(output_dir / 'roc_curves.png', dpi=PLOT_DPI, bbox_inches='tight')
    plt.close()
    print_info("Saved roc_curves.png")

    # --- 5c. Precision-Recall Curve ---
    fig, ax = plt.subplots(figsize=(9, 7))
    for name, y_t, y_p, color in [
        ('CNN', y_true_cnn, y_proba_cnn, PALETTE['CNN']),
        ('MLP', y_true_mlp, y_proba_mlp, PALETTE['MLP']),
    ]:
        prec, rec, _ = precision_recall_curve(y_t, y_p)
        pr_auc = auc(rec, prec)
        ax.plot(rec, prec, label=f'{name} (AP = {pr_auc:.4f})', color=color, linewidth=2)
    ax.set_title('Precision-Recall Curve', fontsize=14, fontweight='bold')
    ax.set_xlabel('Recall')
    ax.set_ylabel('Precision')
    ax.legend(fontsize=11)
    ax.set_xlim([-0.01, 1.01])
    ax.set_ylim([-0.01, 1.01])
    plt.tight_layout()
    plt.savefig(output_dir / 'precision_recall_curves.png', dpi=PLOT_DPI, bbox_inches='tight')
    plt.close()
    print_info("Saved precision_recall_curves.png")

    # --- 5d. Calibration Curves ---
    fig, axes = plt.subplots(1, 2, figsize=(14, 6), sharey=True)
    for ax, name, y_t, y_p, color in [
        (axes[0], 'CNN', y_true_cnn, y_proba_cnn, PALETTE['CNN']),
        (axes[1], 'MLP', y_true_mlp, y_proba_mlp, PALETTE['MLP']),
    ]:
        prob_true, prob_pred = calibration_curve(y_t, y_p, n_bins=10)
        ax.plot(prob_pred, prob_true, 's-', label=name, color=color, linewidth=2, markersize=8)
        ax.plot([0, 1], [0, 1], 'k--', alpha=0.5, label='Perfectly calibrated')
        ax.set_title(f'{name} Calibration Curve', fontsize=14, fontweight='bold')
        ax.set_xlabel('Mean Predicted Probability')
        ax.set_ylabel('Fraction of Positives')
        ax.legend()
    plt.tight_layout()
    plt.savefig(output_dir / 'calibration_curves.png', dpi=PLOT_DPI, bbox_inches='tight')
    plt.close()
    print_info("Saved calibration_curves.png")

    # --- 5e. Confidence Distribution ---
    fig, axes = plt.subplots(1, 2, figsize=(14, 6), sharey=True)
    for ax, name, y_t, y_p in [
        (axes[0], 'CNN', y_true_cnn, y_proba_cnn),
        (axes[1], 'MLP', y_true_mlp, y_proba_mlp),
    ]:
        labels = ['Normal' if l == 0 else 'Noisy' for l in y_t]
        sns.histplot(x=y_p, hue=labels, ax=ax, multiple='stack', bins=30,
                     palette={'Normal': '#4CAF50', 'Noisy': '#F44336'})
        ax.set_title(f'{name} Confidence Distribution', fontsize=14, fontweight='bold')
        ax.set_xlabel('Predicted Probability')
        ax.set_ylabel('Count')
    plt.tight_layout()
    plt.savefig(output_dir / 'confidence_distributions.png', dpi=PLOT_DPI, bbox_inches='tight')
    plt.close()
    print_info("Saved confidence_distributions.png")

    # --- 5f. Metric Comparison ---
    metrics_to_plot = ['f1_score', 'precision', 'recall', 'accuracy', 'specificity', 'mcc']
    cnn_vals = [cnn_data['metrics'][m] for m in metrics_to_plot]
    mlp_vals = [mlp_data['metrics'][m] for m in metrics_to_plot]

    x = np.arange(len(metrics_to_plot))
    width = 0.35

    fig, ax = plt.subplots(figsize=(12, 7))
    bars1 = ax.bar(x - width/2, cnn_vals, width, label='CNN', color=PALETTE['CNN'], edgecolor='white')
    bars2 = ax.bar(x + width/2, mlp_vals, width, label='MLP', color=PALETTE['MLP'], edgecolor='white')

    # Value labels on bars
    for bars in [bars1, bars2]:
        for bar in bars:
            height = bar.get_height()
            ax.annotate(f'{height:.3f}', xy=(bar.get_x() + bar.get_width() / 2, height),
                        xytext=(0, 3), textcoords='offset points', ha='center', va='bottom', fontsize=9)

    ax.set_title('CNN vs MLP: Performance Metrics Comparison', fontsize=14, fontweight='bold')
    ax.set_ylabel('Score')
    ax.set_xticks(x)
    ax.set_xticklabels([m.replace('_', ' ').title() for m in metrics_to_plot])
    ax.legend(fontsize=12)
    ax.set_ylim(0.9, 1.02)
    plt.tight_layout()
    plt.savefig(output_dir / 'metric_comparison.png', dpi=PLOT_DPI, bbox_inches='tight')
    plt.close()
    print_info("Saved metric_comparison.png")

    # --- 5g. Inference Time Comparison ---
    cnn_bd = timing_data['cnn']['breakdown_ms']
    mlp_bd = timing_data['mlp']['breakdown_ms']

    fig, axes = plt.subplots(1, 2, figsize=(14, 6))

    # Stacked bar for CNN
    cnn_stages = ['load', 'preprocess', 'predict']
    cnn_means = [cnn_bd[s]['mean'] for s in cnn_stages]
    colors_cnn = ['#90CAF9', '#42A5F5', '#1565C0']
    bottom = 0
    for stage, val, color in zip(cnn_stages, cnn_means, colors_cnn):
        axes[0].bar('CNN', val, bottom=bottom, color=color, label=stage.title(), edgecolor='white')
        bottom += val

    # Stacked bar for MLP
    mlp_stages = ['extract', 'scale_predict']
    mlp_means = [mlp_bd[s]['mean'] for s in mlp_stages]
    colors_mlp = ['#FFCC80', '#F57C00']
    bottom = 0
    for stage, val, color in zip(mlp_stages, mlp_means, colors_mlp):
        label = 'Extract Features' if stage == 'extract' else 'Scale & Predict'
        axes[0].bar('MLP', val, bottom=bottom, color=color, label=label, edgecolor='white')
        bottom += val

    axes[0].set_title('Mean Inference Time Breakdown', fontsize=14, fontweight='bold')
    axes[0].set_ylabel('Time (ms)')
    axes[0].legend(fontsize=10)

    # Bar chart for total times
    labels = ['CNN\n(Cold Start)', 'CNN\n(Warm Mean)', 'MLP\n(Warm Mean)']
    values = [timing_data['cnn']['cold_start_ms'],
              timing_data['cnn']['warm_total_ms']['mean'],
              timing_data['mlp']['warm_total_ms']['mean']]
    colors = [PALETTE['CNN'], PALETTE['CNN'], PALETTE['MLP']]
    alphas = [0.5, 1.0, 1.0]
    for i, (lbl, val, col, alp) in enumerate(zip(labels, values, colors, alphas)):
        axes[1].bar(lbl, val, color=col, edgecolor='white', alpha=alp)
    axes[1].set_title('Total Inference Time', fontsize=14, fontweight='bold')
    axes[1].set_ylabel('Time (ms)')

    plt.tight_layout()
    plt.savefig(output_dir / 'inference_time_comparison.png', dpi=PLOT_DPI, bbox_inches='tight')
    plt.close()
    print_info("Saved inference_time_comparison.png")

    print_success("All visualizations generated.")


# ==============================================================================
# SECTION 6: CarDetector Benchmark (sklearn cross-validation)
# ==============================================================================

def benchmark_car_detector_cv() -> list | None:
    """Benchmarks CarDetector via 5-fold cross-validation (no pre-trained model needed)."""
    print_header("Section 6: CarDetector Sklearn CV Benchmark")

    if not CAR_DETECTOR_FEATURES_CSV.exists():
        print_error(f"CarDetector features not found: {CAR_DETECTOR_FEATURES_CSV}")
        return None

    df = pd.read_csv(CAR_DETECTOR_FEATURES_CSV).dropna()

    # Use feature list from artifacts if available, otherwise infer from CSV
    meta_cols = {'nfile', 'label', 'reliability', 'length'}
    if (CD_ARTIFACTS / 'features.txt').exists():
        with open(CD_ARTIFACTS / 'features.txt', 'r') as f:
            feature_cols = [line.strip() for line in f if line.strip()]
        # Filter to only features present in CSV
        available = [c for c in feature_cols if c in df.columns]
        missing = [c for c in feature_cols if c not in df.columns]
        if missing:
            print_warning(f"{len(missing)} features from features.txt not in CSV: {missing}")
        feature_cols = available
        print_info(f"Using {len(feature_cols)} features from features.txt")
    else:
        feature_cols = [c for c in df.columns if c not in meta_cols]
        print_warning(f"features.txt not found, using all {len(feature_cols)} columns from CSV")

    X = df[feature_cols].values
    y = df['label'].values
    print_info(f"Dataset: {len(y)} samples, {y.sum()} positive, {len(y) - y.sum()} negative")

    models = {
        'RandomForest': RandomForestClassifier(n_estimators=100, random_state=42),
        'GradientBoosting': GradientBoostingClassifier(n_estimators=100, random_state=42),
        'SVM(RBF)': SVC(kernel='rbf', random_state=42),
        'LogisticRegression': LogisticRegression(max_iter=1000, random_state=42),
        'MLP(64,32)': MLPClassifier(hidden_layer_sizes=(64, 32), max_iter=500, random_state=42),
    }

    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    cv_results = []

    for name, model in tqdm(models.items(), desc="CarDetector CV"):
        pipeline = Pipeline([('scaler', StandardScaler()), ('model', model)])
        scores = cross_validate(pipeline, X, y, cv=cv, scoring=['f1', 'accuracy'], n_jobs=-1)
        cv_results.append({
            'model': name,
            'f1_mean': float(scores['test_f1'].mean()),
            'f1_std': float(scores['test_f1'].std()),
            'accuracy_mean': float(scores['test_accuracy'].mean()),
            'accuracy_std': float(scores['test_accuracy'].std()),
        })

    # Print results table
    print(f"\n{'Model':<22} | {'F1 Score':<22} | {'Accuracy':<22}")
    print("-" * 70)
    for res in sorted(cv_results, key=lambda x: x['f1_mean'], reverse=True):
        f1_str = f"{res['f1_mean']:.4f} +/- {res['f1_std']:.4f}"
        acc_str = f"{res['accuracy_mean']:.4f} +/- {res['accuracy_std']:.4f}"
        print(f"{res['model']:<22} | {f1_str:<22} | {acc_str:<22}")

    return cv_results


# ==============================================================================
# SECTION 7: Dataset Info & JSON Export
# ==============================================================================

def get_dataset_info() -> dict:
    """Gathers statistics about the datasets."""
    def get_info(csv_path: Path) -> dict | None:
        if not csv_path.exists():
            return None
        df = pd.read_csv(csv_path)
        n_samples = len(df)
        n_positive = int(df['label'].sum())
        n_negative = n_samples - n_positive
        return {
            'n_samples': n_samples,
            'n_positive': n_positive,
            'n_negative': n_negative,
            'ratio': round(n_positive / n_samples, 4) if n_samples > 0 else 0,
        }

    return {
        'noisy_car': get_info(NOISY_CAR_ANNOTATION_CSV),
        'car': get_info(CAR_DETECTOR_ANNOTATION_CSV),
    }


def save_json_report(output_dir: Path, **kwargs):
    """Saves all collected metrics to a structured JSON report."""
    print_header("Section 7: Exporting JSON Report")

    def sanitize(o):
        """Makes NumPy types JSON-serializable."""
        if isinstance(o, np.ndarray):
            return o.tolist()
        if isinstance(o, (np.integer,)):
            return int(o)
        if isinstance(o, (np.floating,)):
            return float(o)
        if isinstance(o, (np.bool_,)):
            return bool(o)
        if isinstance(o, Path):
            return str(o)
        return o

    report = {
        'noisy_car_detector': {
            'cnn': {
                'metrics': kwargs['cnn_data']['metrics'],
                'inference_time': kwargs['timing_data']['cnn'],
                'model_size_mb': kwargs['complexity_data']['cnn']['file_size_mb'],
                'n_params': kwargs['complexity_data']['cnn']['total_params'],
                'trainable_params': kwargs['complexity_data']['cnn']['trainable_params'],
            },
            'mlp': {
                'metrics': kwargs['mlp_data']['metrics'],
                'inference_time': kwargs['timing_data']['mlp'],
                'model_size_mb': kwargs['complexity_data']['mlp']['file_size_mb'],
                'n_params': kwargs['complexity_data']['mlp']['total_params'],
                'trainable_params': kwargs['complexity_data']['mlp']['trainable_params'],
            }
        },
        'car_detector': {
            'sklearn_cv_results': kwargs.get('car_detector_cv_data'),
        },
        'dataset_info': kwargs['dataset_info'],
    }

    output_path = output_dir / "report_metrics.json"
    with open(output_path, 'w') as f:
        json.dump(report, f, default=sanitize, indent=2)

    print_success(f"Report saved to {output_path}")
    print_info(f"File size: {os.path.getsize(output_path) / 1024:.1f} KB")


# ==============================================================================
# MAIN
# ==============================================================================

def main():
    """Main execution function."""
    parser = argparse.ArgumentParser(
        description="Comprehensive benchmark of pre-trained audio classification models."
    )
    parser.add_argument(
        '--output-dir', type=str, default='benchmark_results',
        help='Directory to save results (relative to project root, default: benchmark_results)'
    )
    parser.add_argument(
        '--n-timing-samples', type=int, default=50,
        help='Number of audio samples for inference timing benchmark (default: 50)'
    )
    args = parser.parse_args()

    output_dir = PROJECT_ROOT / args.output_dir
    output_dir.mkdir(exist_ok=True)
    print_info(f"Output directory: {output_dir}")

    # --- Section 1: CNN Evaluation ---
    cnn_data = evaluate_noisy_car_cnn(output_dir)

    # --- Section 2: MLP Evaluation ---
    mlp_data = evaluate_noisy_car_mlp(output_dir)

    if cnn_data is None or mlp_data is None:
        print_error("Cannot proceed without both NoisyCarDetector models. Exiting.")
        return 1

    # --- Section 3: Inference Time ---
    timing_data = benchmark_inference_time(args.n_timing_samples, cnn_data, mlp_data)

    # --- Section 4: Model Complexity ---
    complexity_data = analyze_model_complexity(cnn_data, mlp_data)

    # --- Section 5: Visualizations ---
    generate_visualizations(output_dir, cnn_data, mlp_data, timing_data)

    # --- Section 6: CarDetector CV ---
    car_detector_cv_data = benchmark_car_detector_cv()

    # --- Section 7: JSON Export ---
    dataset_info = get_dataset_info()
    save_json_report(
        output_dir=output_dir,
        cnn_data=cnn_data,
        mlp_data=mlp_data,
        timing_data=timing_data,
        complexity_data=complexity_data,
        car_detector_cv_data=car_detector_cv_data,
        dataset_info=dataset_info,
    )

    print_header("BENCHMARK COMPLETE")
    print_success(f"All results saved to {output_dir}/")
    return 0


if __name__ == "__main__":
    sys.exit(main())
