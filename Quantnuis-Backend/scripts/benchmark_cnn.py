#!/usr/bin/env python3
"""
================================================================================
                    BENCHMARK DU MODELE CNN (NoisyCarDetector)
================================================================================

Évalue le modèle CNN pré-entraîné sur les données locales et compare
avec les modèles sklearn classiques.

Usage:
    python -m scripts.benchmark_cnn                     # Benchmark CNN seul
    python -m scripts.benchmark_cnn --compare            # + comparaison sklearn
    python -m scripts.benchmark_cnn --output-dir results # Dossier de sortie

================================================================================
"""

import sys
import argparse
import json
import warnings
from pathlib import Path

warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", category=UserWarning)

import numpy as np
import pandas as pd
import librosa
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.model_selection import StratifiedKFold, cross_val_score
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score,
    confusion_matrix, classification_report, roc_curve, auc,
)
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.svm import SVC
from sklearn.neighbors import KNeighborsClassifier
from sklearn.naive_bayes import GaussianNB
from sklearn.neural_network import MLPClassifier
from imblearn.over_sampling import SMOTE
from imblearn.pipeline import Pipeline as ImbPipeline

try:
    from tqdm import tqdm
except ImportError:
    def tqdm(iterable, *args, **kwargs):
        return iterable

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from shared import print_header, print_info, print_success, print_warning, print_error, Colors

import tensorflow as tf

# ==============================================================================
# CHEMINS
# ==============================================================================

DATA_DIR = PROJECT_ROOT / "data" / "noisy_car_detector"
SLICES_DIR = DATA_DIR / "slices"
ANNOTATION_CSV = DATA_DIR / "annotation.csv"
FEATURES_CSV = DATA_DIR / "features_optimized.csv"
CNN_MODEL_PATH = PROJECT_ROOT / "models" / "noisy_car_detector" / "artifacts" / "cnn_noisy_car.h5"
CNN_CONFIG_PATH = PROJECT_ROOT / "models" / "noisy_car_detector" / "artifacts" / "cnn_config.json"


# ==============================================================================
# PREPROCESSING
# ==============================================================================

def preprocess_audio(file_path: Path, cfg: dict) -> np.ndarray:
    """Génère le mel-spectrogramme normalisé (pipeline identique à production)."""
    y, _ = librosa.load(file_path, sr=cfg['sr'], duration=cfg['duration'])

    target_len = int(cfg['sr'] * cfg['duration'])
    if len(y) < target_len:
        y = np.pad(y, (0, target_len - len(y)), mode='constant')
    else:
        y = y[:target_len]

    y = librosa.util.normalize(y)

    mel = librosa.feature.melspectrogram(
        y=y, sr=cfg['sr'], n_mels=cfg['n_mels'],
        n_fft=cfg['n_fft'], hop_length=cfg['hop_length']
    )
    mel_db = librosa.power_to_db(mel, ref=np.max)
    mel_norm = (mel_db - cfg['X_mean']) / (cfg['X_std'] + 1e-8)

    return mel_norm


# ==============================================================================
# BENCHMARK CNN
# ==============================================================================

def benchmark_cnn(output_dir: Path):
    """Évalue le CNN sur tous les slices annotés."""

    print_header("BENCHMARK CNN - NoisyCarDetector")

    # Charger config + modèle
    with open(CNN_CONFIG_PATH, 'r') as f:
        cfg = json.load(f)
    print_info(f"Config CNN: {cfg['n_mels']} mels, {cfg['sr']} Hz, {cfg['duration']}s")
    print_info(f"Entraîné sur {cfg.get('n_samples', '?')} samples (CV F1={cfg.get('cv_f1_mean', '?'):.4f})")

    model = tf.keras.models.load_model(str(CNN_MODEL_PATH))
    print_success("Modèle CNN chargé")

    # Charger annotations
    annotations = pd.read_csv(ANNOTATION_CSV)
    print_info(f"Annotations: {len(annotations)} samples")

    # Distribution
    n_pos = (annotations['label'] == 1).sum()
    n_neg = (annotations['label'] == 0).sum()
    print_info(f"  Bruyant: {n_pos} ({n_pos/len(annotations)*100:.1f}%)")
    print_info(f"  Normal:  {n_neg} ({n_neg/len(annotations)*100:.1f}%)")

    # Prédictions par batch
    batch_size = 32
    y_true = []
    y_proba = []
    processed_files = []
    errors_list = []

    nfiles = annotations['nfile'].tolist()
    labels = annotations['label'].astype(int).tolist()

    for i in tqdm(range(0, len(nfiles), batch_size), desc="CNN predictions"):
        batch_nfiles = nfiles[i:i + batch_size]
        batch_labels = labels[i:i + batch_size]

        batch_X = []
        batch_valid_labels = []
        batch_valid_files = []

        for nfile, label in zip(batch_nfiles, batch_labels):
            path = SLICES_DIR / nfile
            if not path.exists():
                errors_list.append(f"Fichier manquant: {nfile}")
                continue
            try:
                mel = preprocess_audio(path, cfg)
                batch_X.append(mel)
                batch_valid_labels.append(label)
                batch_valid_files.append(nfile)
            except Exception as e:
                errors_list.append(f"Erreur {nfile}: {e}")

        if not batch_X:
            continue

        # Stack: (batch, n_mels, time, 1)
        X_batch = np.array(batch_X)[..., np.newaxis]
        preds = model.predict(X_batch, verbose=0).flatten()

        y_proba.extend(preds)
        y_true.extend(batch_valid_labels)
        processed_files.extend(batch_valid_files)

    if errors_list:
        print_warning(f"{len(errors_list)} erreurs de traitement")
        for err in errors_list[:5]:
            print_warning(f"  {err}")

    y_true = np.array(y_true)
    y_proba = np.array(y_proba)
    y_pred = (y_proba > 0.5).astype(int)

    # Métriques
    print_header("RÉSULTATS CNN")

    acc = accuracy_score(y_true, y_pred)
    prec = precision_score(y_true, y_pred)
    rec = recall_score(y_true, y_pred)
    f1 = f1_score(y_true, y_pred)

    print(f"\n  Accuracy:  {acc:.4f}")
    print(f"  Precision: {prec:.4f}")
    print(f"  Recall:    {rec:.4f}")
    print(f"  {Colors.GREEN}F1 Score:  {f1:.4f}{Colors.END}")
    print()
    print(classification_report(y_true, y_pred, target_names=['Normal (0)', 'Bruyant (1)']))

    cm = confusion_matrix(y_true, y_pred)
    print(f"  Confusion: TN={cm[0,0]} FP={cm[0,1]} FN={cm[1,0]} TP={cm[1,1]}")

    cnn_metrics = {
        'Model': 'CNN (mel-spectrogram)',
        'F1 Mean': f1,
        'F1 Std': 0.0,
        'Acc Mean': acc,
        'Acc Std': 0.0,
    }

    return y_true, y_proba, y_pred, processed_files, cnn_metrics


# ==============================================================================
# ANALYSE DÉTAILLÉE CNN
# ==============================================================================

def analyze_cnn(y_true, y_proba, y_pred, processed_files, output_dir: Path):
    """Analyse détaillée: distribution probas, erreurs, ROC, confusion matrix."""

    print_header("ANALYSE DÉTAILLÉE CNN")

    # 1. Histogramme des probabilités
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))

    ax = axes[0]
    mask_pos = y_true == 1
    mask_neg = y_true == 0
    ax.hist(y_proba[mask_neg], bins=50, alpha=0.7, label='Normal (0)', color='#3498db')
    ax.hist(y_proba[mask_pos], bins=50, alpha=0.7, label='Bruyant (1)', color='#e74c3c')
    ax.axvline(0.5, color='black', linestyle='--', linewidth=1.5, label='Seuil 0.5')
    ax.set_xlabel('Probabilité CNN')
    ax.set_ylabel('Fréquence')
    ax.set_title('Distribution des probabilités par classe')
    ax.legend()
    ax.grid(True, alpha=0.3)

    # 2. ROC curve
    fpr, tpr, _ = roc_curve(y_true, y_proba)
    roc_auc = auc(fpr, tpr)

    ax = axes[1]
    ax.plot(fpr, tpr, color='#e74c3c', lw=2, label=f'ROC (AUC = {roc_auc:.4f})')
    ax.plot([0, 1], [0, 1], color='gray', lw=1, linestyle='--')
    ax.set_xlabel('False Positive Rate')
    ax.set_ylabel('True Positive Rate')
    ax.set_title('ROC Curve - CNN')
    ax.legend(loc='lower right')
    ax.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig(output_dir / 'cnn_analysis.png', dpi=150, bbox_inches='tight')
    plt.close()
    print_success(f"Sauvegardé: {output_dir / 'cnn_analysis.png'}")

    # 3. Confusion matrix heatmap
    cm = confusion_matrix(y_true, y_pred)
    fig, ax = plt.subplots(figsize=(7, 5))
    sns.heatmap(cm, annot=True, fmt='d', cmap='Blues',
                xticklabels=['Normal', 'Bruyant'],
                yticklabels=['Normal', 'Bruyant'], ax=ax)
    ax.set_xlabel('Prédit')
    ax.set_ylabel('Réel')
    ax.set_title('Matrice de Confusion - CNN')
    plt.tight_layout()
    plt.savefig(output_dir / 'cnn_confusion_matrix.png', dpi=150, bbox_inches='tight')
    plt.close()
    print_success(f"Sauvegardé: {output_dir / 'cnn_confusion_matrix.png'}")

    # 4. Erreurs du CNN
    misclassified = []
    for i in range(len(y_true)):
        if y_true[i] != y_pred[i]:
            misclassified.append({
                'file': processed_files[i],
                'probability': y_proba[i],
                'true_label': int(y_true[i]),
                'predicted': int(y_pred[i]),
            })

    if misclassified:
        print_warning(f"\n{len(misclassified)} échantillons mal classifiés:")
        # Trier par confiance décroissante (les erreurs les plus "confiantes")
        misclassified.sort(key=lambda x: abs(x['probability'] - 0.5), reverse=True)
        for m in misclassified[:15]:
            true_str = "Bruyant" if m['true_label'] == 1 else "Normal"
            pred_str = "Bruyant" if m['predicted'] == 1 else "Normal"
            print(f"  {m['file']}: proba={m['probability']:.4f} | réel={true_str} | prédit={pred_str}")

        if len(misclassified) > 15:
            print(f"  ... et {len(misclassified) - 15} autres")
    else:
        print_success("Aucune erreur de classification!")

    print_info(f"\nAUC: {roc_auc:.4f}")


# ==============================================================================
# COMPARAISON SKLEARN
# ==============================================================================

def compare_with_sklearn(cnn_metrics: dict, output_dir: Path, use_smote: bool = False):
    """Compare le CNN avec les modèles sklearn sur features tabulaires."""

    smote_str = " (+ SMOTE)" if use_smote else ""
    print_header(f"COMPARAISON CNN vs SKLEARN{smote_str}")

    # Charger features
    df = pd.read_csv(FEATURES_CSV)
    print_info(f"Features tabulaires: {df.shape[0]} samples, {df.shape[1] - 3} features")

    meta_cols = ['nfile', 'label', 'reliability']
    feature_cols = [c for c in df.columns if c not in meta_cols]

    X = df[feature_cols].values
    y = df['label'].astype(int).values
    X = np.nan_to_num(X, nan=0.0, posinf=0.0, neginf=0.0)

    # Distribution avant SMOTE
    n_pos = (y == 1).sum()
    n_neg = (y == 0).sum()
    print_info(f"  Bruyant: {n_pos} ({n_pos/len(y)*100:.1f}%)")
    print_info(f"  Normal:  {n_neg} ({n_neg/len(y)*100:.1f}%)")

    if use_smote:
        minority = min(n_pos, n_neg)
        k = min(5, minority - 1)
        k = max(1, k)
        print_info(f"  SMOTE activé (k_neighbors={k})")

    # Modèles sklearn
    sklearn_models = {
        'Logistic Regression': LogisticRegression(max_iter=1000, random_state=42),
        'Random Forest': RandomForestClassifier(n_estimators=100, random_state=42, n_jobs=-1),
        'Gradient Boosting': GradientBoostingClassifier(n_estimators=100, random_state=42),
        'SVM (RBF)': SVC(kernel='rbf', probability=True, random_state=42),
        'SVM (Linear)': SVC(kernel='linear', probability=True, random_state=42),
        'KNN (k=5)': KNeighborsClassifier(n_neighbors=5),
        'KNN (k=3)': KNeighborsClassifier(n_neighbors=3),
        'Naive Bayes': GaussianNB(),
        'MLP (32)': MLPClassifier(hidden_layer_sizes=(32,), max_iter=500, random_state=42),
        'MLP (64, 32)': MLPClassifier(hidden_layer_sizes=(64, 32), max_iter=500, random_state=42),
    }

    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    results = []

    for name, model in tqdm(sklearn_models.items(), desc="Sklearn models"):
        try:
            if use_smote:
                # SMOTE dans un pipeline imblearn → appliqué uniquement sur le train fold
                minority_count = min(n_pos, n_neg)
                k_smote = min(5, minority_count - 1)
                k_smote = max(1, k_smote)
                pipeline = ImbPipeline([
                    ('scaler', StandardScaler()),
                    ('smote', SMOTE(k_neighbors=k_smote, random_state=42)),
                    ('model', model),
                ])
                f1_scores = cross_val_score(pipeline, X, y, cv=cv, scoring='f1', n_jobs=-1)
                acc_scores = cross_val_score(pipeline, X, y, cv=cv, scoring='accuracy', n_jobs=-1)
            else:
                scaler = StandardScaler()
                X_scaled = scaler.fit_transform(X)
                f1_scores = cross_val_score(model, X_scaled, y, cv=cv, scoring='f1', n_jobs=-1)
                acc_scores = cross_val_score(model, X_scaled, y, cv=cv, scoring='accuracy', n_jobs=-1)

            results.append({
                'Model': name,
                'F1 Mean': f1_scores.mean(),
                'F1 Std': f1_scores.std(),
                'Acc Mean': acc_scores.mean(),
                'Acc Std': acc_scores.std(),
            })
        except Exception as e:
            print_warning(f"  {name}: {e}")

    # Ajouter le CNN
    results.append(cnn_metrics)

    # Trier par F1
    results.sort(key=lambda x: x['F1 Mean'], reverse=True)

    # Afficher
    print()
    print(f"{'Model':<25} {'F1 Score':<20} {'Accuracy':<20}")
    print("-" * 65)
    for r in results:
        f1_str = f"{r['F1 Mean']:.4f} (±{r['F1 Std']*2:.4f})"
        acc_str = f"{r['Acc Mean']:.4f} (±{r['Acc Std']*2:.4f})"
        marker = " ★" if 'CNN' in r['Model'] else ""
        print(f"{r['Model']:<25} {f1_str:<20} {acc_str:<20}{marker}")

    print()
    best = results[0]
    print_success(f"Meilleur modèle: {best['Model']} (F1={best['F1 Mean']:.4f})")

    # Graphique comparatif
    fig, ax = plt.subplots(figsize=(12, 7))

    models_names = [r['Model'] for r in results]
    f1_means = [r['F1 Mean'] for r in results]
    f1_stds = [r['F1 Std'] for r in results]

    colors = ['#e74c3c' if 'CNN' in name else '#3498db' for name in models_names]

    bars = ax.barh(models_names, f1_means, xerr=f1_stds, color=colors,
                   alpha=0.85, capsize=5, edgecolor='white', linewidth=0.5)
    ax.set_xlabel('F1 Score')
    ax.set_title(f'Comparaison CNN vs Sklearn{smote_str} - NoisyCarDetector')
    ax.set_xlim(0, 1.05)
    ax.grid(axis='x', alpha=0.3)

    for bar, mean in zip(bars, f1_means):
        ax.text(mean + 0.015, bar.get_y() + bar.get_height() / 2,
                f'{mean:.4f}', va='center', fontsize=9)

    plt.tight_layout()
    suffix = '_smote' if use_smote else ''
    plt.savefig(output_dir / f'cnn_vs_sklearn_comparison{suffix}.png', dpi=150, bbox_inches='tight')
    plt.close()
    print_success(f"Sauvegardé: {output_dir / 'cnn_vs_sklearn_comparison.png'}")

    return results


# ==============================================================================
# MAIN
# ==============================================================================

def main():
    parser = argparse.ArgumentParser(description='Benchmark CNN NoisyCarDetector')
    parser.add_argument('--compare', action='store_true',
                        help='Comparer avec les modèles sklearn')
    parser.add_argument('--smote', action='store_true',
                        help='Utiliser SMOTE pour augmenter les données sklearn')
    parser.add_argument('--output-dir', type=str, default='benchmark_results',
                        help='Dossier de sortie (default: benchmark_results)')
    args = parser.parse_args()

    output_dir = PROJECT_ROOT / args.output_dir
    output_dir.mkdir(exist_ok=True)

    # 1. Benchmark CNN
    result = benchmark_cnn(output_dir)
    if result is None:
        print_error("Échec du benchmark CNN")
        return 1

    y_true, y_proba, y_pred, processed_files, cnn_metrics = result

    # 2. Analyse détaillée
    analyze_cnn(y_true, y_proba, y_pred, processed_files, output_dir)

    # 3. Comparaison sklearn (optionnel)
    if args.compare:
        compare_with_sklearn(cnn_metrics, output_dir, use_smote=args.smote)

    print()
    print_success(f"Benchmark terminé. Résultats dans: {output_dir}")
    return 0


if __name__ == "__main__":
    try:
        exit(main())
    except KeyboardInterrupt:
        print("\nAnnulé")
        exit(130)
