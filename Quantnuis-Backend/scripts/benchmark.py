#!/usr/bin/env python3
"""
================================================================================
                    BENCHMARK DES MODELES ET ANALYSE DES FEATURES
================================================================================

Script pour:
1. Analyser la qualite des features (clustering, separabilite)
2. Comparer plusieurs modeles (Logistic Regression, RF, SVM, NN)
3. Detecter l'overfitting avec learning curves
4. Recommander le meilleur modele

Usage:
    python -m scripts.benchmark --model car_detector
    python -m scripts.benchmark --model noisy_car_detector
    python -m shared.benchmark --model car_detector --add-features

================================================================================
"""

import argparse
import warnings
import os
import sys

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path

# ML imports
from sklearn.model_selection import (
    cross_val_score, StratifiedKFold, learning_curve, train_test_split
)
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.svm import SVC
from sklearn.neighbors import KNeighborsClassifier
from sklearn.naive_bayes import GaussianNB
from sklearn.neural_network import MLPClassifier
from sklearn.decomposition import PCA
from sklearn.manifold import TSNE
from sklearn.metrics import (
    classification_report, confusion_matrix, f1_score,
    accuracy_score, precision_score, recall_score
)

warnings.filterwarnings('ignore')

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from shared import print_header, print_info, print_success, print_warning, print_error


# ==============================================================================
# CONFIGURATION
# ==============================================================================

MODELS_CONFIG = {
    'car_detector': {
        'features_csv': PROJECT_ROOT / 'data' / 'car_detector' / 'features_all.csv',
        'features_optimized_csv': PROJECT_ROOT / 'data' / 'car_detector' / 'features_optimized.csv',
        'label_col': 'label',
        'positive_label': 'Vehicule detecte',
        'negative_label': 'Pas de vehicule',
    },
    'noisy_car_detector': {
        'features_csv': PROJECT_ROOT / 'data' / 'noisy_car_detector' / 'features_all.csv',
        'features_optimized_csv': PROJECT_ROOT / 'data' / 'noisy_car_detector' / 'features_optimized.csv',
        'label_col': 'label',
        'positive_label': 'Vehicule bruyant',
        'negative_label': 'Vehicule normal',
    }
}

# Modeles a comparer
MODELS_TO_COMPARE = {
    'Logistic Regression': LogisticRegression(max_iter=1000, random_state=42),
    'Random Forest': RandomForestClassifier(n_estimators=100, random_state=42, n_jobs=-1),
    'Gradient Boosting': GradientBoostingClassifier(n_estimators=100, random_state=42),
    'SVM (RBF)': SVC(kernel='rbf', probability=True, random_state=42),
    'SVM (Linear)': SVC(kernel='linear', probability=True, random_state=42),
    'KNN (k=5)': KNeighborsClassifier(n_neighbors=5),
    'KNN (k=3)': KNeighborsClassifier(n_neighbors=3),
    'Naive Bayes': GaussianNB(),
    'MLP (small)': MLPClassifier(hidden_layer_sizes=(32,), max_iter=500, random_state=42),
    'MLP (current)': MLPClassifier(hidden_layer_sizes=(64, 32), max_iter=500, random_state=42),
}


# ==============================================================================
# DATA LOADING
# ==============================================================================

def load_features(model_name: str, use_optimized: bool = False) -> tuple:
    """Charge les features et labels."""
    config = MODELS_CONFIG[model_name]

    # Choisir le fichier de features
    if use_optimized and config['features_optimized_csv'].exists():
        csv_path = config['features_optimized_csv']
        print_info(f"Utilisation des features optimisees: {csv_path.name}")
    else:
        csv_path = config['features_csv']
        if use_optimized:
            print_warning("Fichier de features optimisees non trouve, utilisation du fichier complet")

    df = pd.read_csv(csv_path)

    # Separer features et labels
    label_col = config['label_col']
    feature_cols = [c for c in df.columns if c not in [label_col, 'nfile', 'file', 'filename', 'reliability']]

    X = df[feature_cols].values
    y = df[label_col].values

    # Remplacer NaN par 0
    X = np.nan_to_num(X, nan=0.0, posinf=0.0, neginf=0.0)

    return X, y, feature_cols, df


# ==============================================================================
# FEATURE ANALYSIS
# ==============================================================================

def analyze_features(X: np.ndarray, y: np.ndarray, feature_names: list, model_name: str):
    """Analyse la qualite des features."""

    print_header("ANALYSE DES FEATURES")

    # Stats de base
    print_info(f"Nombre d'echantillons: {X.shape[0]}")
    print_info(f"Nombre de features: {X.shape[1]}")

    unique, counts = np.unique(y, return_counts=True)
    print_info("Distribution des classes:")
    for label, count in zip(unique, counts):
        pct = count / len(y) * 100
        print_info(f"  Classe {label}: {count} ({pct:.1f}%)")

    # Variance des features
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    variances = np.var(X_scaled, axis=0)
    low_var_features = [f for f, v in zip(feature_names, variances) if v < 0.1]

    if low_var_features:
        print_warning(f"{len(low_var_features)} features avec faible variance:")
        for f in low_var_features[:5]:
            print_warning(f"  - {f}")

    # Correlation avec le label
    correlations = []
    for i, fname in enumerate(feature_names):
        corr = np.corrcoef(X[:, i], y)[0, 1]
        if not np.isnan(corr):
            correlations.append((fname, abs(corr)))

    correlations.sort(key=lambda x: x[1], reverse=True)

    print_info("\nTop 10 features correlees au label:")
    for fname, corr in correlations[:10]:
        print_info(f"  {fname}: {corr:.3f}")

    print_info("\nFeatures les moins correlees:")
    for fname, corr in correlations[-5:]:
        print_warning(f"  {fname}: {corr:.3f}")

    return X_scaled, correlations


def visualize_clusters(X: np.ndarray, y: np.ndarray, display_name: str, output_dir: Path, file_label: str = None):
    """Visualise les clusters avec PCA et t-SNE."""

    if file_label is None:
        file_label = display_name.replace(' ', '_').lower()

    print_header("VISUALISATION DES CLUSTERS")

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    fig, axes = plt.subplots(1, 3, figsize=(18, 5))

    # 1. PCA 2D
    print_info("Calcul PCA...")
    pca = PCA(n_components=2)
    X_pca = pca.fit_transform(X_scaled)

    ax = axes[0]
    scatter = ax.scatter(X_pca[:, 0], X_pca[:, 1], c=y, cmap='coolwarm', alpha=0.6, edgecolors='k', linewidth=0.5)
    ax.set_xlabel(f'PC1 ({pca.explained_variance_ratio_[0]*100:.1f}%)')
    ax.set_ylabel(f'PC2 ({pca.explained_variance_ratio_[1]*100:.1f}%)')
    ax.set_title(f'PCA - {display_name}')
    plt.colorbar(scatter, ax=ax, label='Classe')

    # Variance expliquee
    total_var = sum(pca.explained_variance_ratio_[:2]) * 100
    print_info(f"Variance expliquee (2 composantes): {total_var:.1f}%")

    # 2. PCA avec plus de composantes
    pca_full = PCA(n_components=min(10, X.shape[1]))
    pca_full.fit(X_scaled)

    ax = axes[1]
    cumvar = np.cumsum(pca_full.explained_variance_ratio_) * 100
    ax.bar(range(1, len(cumvar)+1), pca_full.explained_variance_ratio_*100, alpha=0.7, label='Individuelle')
    ax.plot(range(1, len(cumvar)+1), cumvar, 'r-o', label='Cumulative')
    ax.axhline(y=90, color='g', linestyle='--', label='90% seuil')
    ax.set_xlabel('Composante')
    ax.set_ylabel('Variance expliquee (%)')
    ax.set_title('Variance par composante PCA')
    ax.legend()

    n_components_90 = np.argmax(cumvar >= 90) + 1
    print_info(f"Composantes pour 90% variance: {n_components_90}")

    # 3. t-SNE
    print_info("Calcul t-SNE (peut prendre du temps)...")
    tsne = TSNE(n_components=2, random_state=42, perplexity=min(30, X.shape[0]//4))
    X_tsne = tsne.fit_transform(X_scaled)

    ax = axes[2]
    scatter = ax.scatter(X_tsne[:, 0], X_tsne[:, 1], c=y, cmap='coolwarm', alpha=0.6, edgecolors='k', linewidth=0.5)
    ax.set_xlabel('t-SNE 1')
    ax.set_ylabel('t-SNE 2')
    ax.set_title(f't-SNE - {display_name}')
    plt.colorbar(scatter, ax=ax, label='Classe')

    plt.tight_layout()

    # Save figure
    output_path = output_dir / f'clusters_{file_label}.png'
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    print_success(f"Figure sauvegardee: {output_path}")

    plt.close()

    # Evaluer la separabilite
    from sklearn.metrics import silhouette_score
    try:
        sil_score = silhouette_score(X_scaled, y)
        print_info(f"\nSilhouette Score: {sil_score:.3f}")
        if sil_score < 0.2:
            print_warning("Score faible: les clusters ne sont pas bien separes!")
        elif sil_score < 0.5:
            print_warning("Score moyen: separation moderee des clusters")
        else:
            print_success("Bon score: clusters bien separes")
    except:
        print_warning("Impossible de calculer le Silhouette Score")


# ==============================================================================
# MODEL COMPARISON
# ==============================================================================

def compare_models(X: np.ndarray, y: np.ndarray, display_name: str, output_dir: Path, file_label: str = None):
    """Compare plusieurs modeles avec cross-validation."""

    if file_label is None:
        file_label = display_name.replace(' ', '_').lower()

    print_header("COMPARAISON DES MODELES")

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)

    results = []

    for name, model in MODELS_TO_COMPARE.items():
        print_info(f"Evaluation: {name}...")

        try:
            # Cross-validation scores
            f1_scores = cross_val_score(model, X_scaled, y, cv=cv, scoring='f1', n_jobs=-1)
            acc_scores = cross_val_score(model, X_scaled, y, cv=cv, scoring='accuracy', n_jobs=-1)

            results.append({
                'Model': name,
                'F1 Mean': f1_scores.mean(),
                'F1 Std': f1_scores.std(),
                'Acc Mean': acc_scores.mean(),
                'Acc Std': acc_scores.std(),
                'F1 Scores': f1_scores
            })
        except Exception as e:
            print_warning(f"  Erreur: {e}")

    # Sort by F1 score
    results.sort(key=lambda x: x['F1 Mean'], reverse=True)

    # Display results
    print_header("RESULTATS (tries par F1 Score)")
    print()
    print(f"{'Model':<25} {'F1 Score':<20} {'Accuracy':<20}")
    print("-" * 65)

    for r in results:
        f1_str = f"{r['F1 Mean']:.3f} (+/- {r['F1 Std']*2:.3f})"
        acc_str = f"{r['Acc Mean']:.3f} (+/- {r['Acc Std']*2:.3f})"
        print(f"{r['Model']:<25} {f1_str:<20} {acc_str:<20}")

    # Highlight best models
    print()
    best = results[0]
    print_success(f"Meilleur modele: {best['Model']} (F1={best['F1 Mean']:.3f})")

    # Compare with MLP (current architecture)
    mlp_result = next((r for r in results if 'MLP (current)' in r['Model']), None)
    if mlp_result:
        diff = best['F1 Mean'] - mlp_result['F1 Mean']
        if diff > 0.01:
            print_warning(f"Le NN actuel est {diff*100:.1f}% moins bon que {best['Model']}")

    # Visualize comparison
    fig, ax = plt.subplots(figsize=(12, 6))

    models_names = [r['Model'] for r in results]
    f1_means = [r['F1 Mean'] for r in results]
    f1_stds = [r['F1 Std'] for r in results]

    colors = ['#2ecc71' if r['Model'] == best['Model'] else '#3498db' for r in results]

    bars = ax.barh(models_names, f1_means, xerr=f1_stds, color=colors, alpha=0.8, capsize=5)
    ax.set_xlabel('F1 Score')
    ax.set_title(f'Comparaison des modeles - {display_name}')
    ax.set_xlim(0, 1)

    # Add value labels
    for bar, mean in zip(bars, f1_means):
        ax.text(mean + 0.02, bar.get_y() + bar.get_height()/2, f'{mean:.3f}', va='center')

    plt.tight_layout()

    output_path = output_dir / f'model_comparison_{file_label}.png'
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    print_success(f"Figure sauvegardee: {output_path}")

    plt.close()

    return results


# ==============================================================================
# OVERFITTING DETECTION
# ==============================================================================

def detect_overfitting(X: np.ndarray, y: np.ndarray, display_name: str, output_dir: Path, file_label: str = None):
    """Detecte l'overfitting avec learning curves."""

    if file_label is None:
        file_label = display_name.replace(' ', '_').lower()

    print_header("DETECTION D'OVERFITTING")

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    # Models to check
    models_to_check = {
        'Logistic Regression': LogisticRegression(max_iter=1000, random_state=42),
        'Random Forest': RandomForestClassifier(n_estimators=100, random_state=42),
        'MLP (current)': MLPClassifier(hidden_layer_sizes=(64, 32), max_iter=500, random_state=42),
    }

    fig, axes = plt.subplots(1, 3, figsize=(15, 4))

    for idx, (name, model) in enumerate(models_to_check.items()):
        print_info(f"Learning curve: {name}...")

        train_sizes, train_scores, val_scores = learning_curve(
            model, X_scaled, y,
            cv=5,
            n_jobs=-1,
            train_sizes=np.linspace(0.1, 1.0, 10),
            scoring='f1',
            random_state=42
        )

        train_mean = train_scores.mean(axis=1)
        train_std = train_scores.std(axis=1)
        val_mean = val_scores.mean(axis=1)
        val_std = val_scores.std(axis=1)

        ax = axes[idx]
        ax.fill_between(train_sizes, train_mean - train_std, train_mean + train_std, alpha=0.1, color='blue')
        ax.fill_between(train_sizes, val_mean - val_std, val_mean + val_std, alpha=0.1, color='orange')
        ax.plot(train_sizes, train_mean, 'o-', color='blue', label='Train')
        ax.plot(train_sizes, val_mean, 'o-', color='orange', label='Validation')
        ax.set_xlabel('Taille du dataset')
        ax.set_ylabel('F1 Score')
        ax.set_title(name)
        ax.legend(loc='lower right')
        ax.set_ylim(0, 1.1)
        ax.grid(True, alpha=0.3)

        # Detect overfitting
        gap = train_mean[-1] - val_mean[-1]
        if gap > 0.1:
            print_warning(f"  {name}: OVERFITTING detecte (gap={gap:.2f})")
        elif gap > 0.05:
            print_warning(f"  {name}: Leger overfitting (gap={gap:.2f})")
        else:
            print_success(f"  {name}: Pas d'overfitting (gap={gap:.2f})")

    plt.tight_layout()

    output_path = output_dir / f'learning_curves_{file_label}.png'
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    print_success(f"Figure sauvegardee: {output_path}")

    plt.close()


# ==============================================================================
# IMPROVED FEATURES FOR VEHICLE DETECTION
# ==============================================================================

def suggest_new_features():
    """Suggere des features supplementaires pour la detection de vehicules."""

    print_header("FEATURES RECOMMANDEES POUR VEHICULES")

    suggestions = """
Les vehicules ont des caracteristiques audio specifiques:

1. BASSES FREQUENCES (moteur, echappement)
   - Energie dans les bandes 20-200 Hz
   - Ratio basses/hautes frequences
   - Sous-bandes du mel spectrogram (bandes 0-5)

2. CARACTERISTIQUES TEMPORELLES
   - Onset strength (debut des sons)
   - Delta MFCC (changement temporel)
   - Delta-delta MFCC (acceleration)

3. PATTERNS DE BRUIT DE MOTEUR
   - Periodicite du signal (autocorrelation)
   - Frequence fondamentale estimee
   - Harmoniques du moteur

4. FEATURES SPECTROGRAMME
   - Statistiques sur mel-spectrogram
   - Energie par bande de frequence
   - Variation temporelle du spectre

Code pour ajouter ces features dans audio_utils.py:

```python
def extract_vehicle_features(y: np.ndarray, sr: int) -> dict:
    features = {}

    # 1. Energie basses frequences
    S = np.abs(librosa.stft(y))
    freqs = librosa.fft_frequencies(sr=sr)
    low_freq_mask = freqs < 200
    high_freq_mask = freqs >= 200

    features['low_freq_energy'] = float(np.mean(S[low_freq_mask, :]))
    features['high_freq_energy'] = float(np.mean(S[high_freq_mask, :]))
    features['low_high_ratio'] = features['low_freq_energy'] / (features['high_freq_energy'] + 1e-10)

    # 2. Delta MFCC
    mfccs = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=13)
    delta_mfcc = librosa.feature.delta(mfccs)
    delta2_mfcc = librosa.feature.delta(mfccs, order=2)

    for i in range(13):
        features[f'delta_mfcc_{i+1}_mean'] = float(np.mean(delta_mfcc[i]))
        features[f'delta2_mfcc_{i+1}_mean'] = float(np.mean(delta2_mfcc[i]))

    # 3. Mel spectrogram par bande
    mel_spec = librosa.feature.melspectrogram(y=y, sr=sr, n_mels=128)
    mel_db = librosa.power_to_db(mel_spec)

    # Bandes: 0-10 (basses), 10-40 (mediums), 40-128 (aigus)
    features['mel_low_mean'] = float(np.mean(mel_db[:10, :]))
    features['mel_mid_mean'] = float(np.mean(mel_db[10:40, :]))
    features['mel_high_mean'] = float(np.mean(mel_db[40:, :]))

    # 4. Onset strength
    onset_env = librosa.onset.onset_strength(y=y, sr=sr)
    features['onset_mean'] = float(np.mean(onset_env))
    features['onset_std'] = float(np.std(onset_env))
    features['onset_max'] = float(np.max(onset_env))

    # 5. Spectral flux (changement spectral)
    spectral_flux = np.sqrt(np.sum(np.diff(S, axis=1)**2, axis=0))
    features['spectral_flux_mean'] = float(np.mean(spectral_flux))
    features['spectral_flux_std'] = float(np.std(spectral_flux))

    return features
```
"""
    print(suggestions)


# ==============================================================================
# MAIN
# ==============================================================================

def main():
    parser = argparse.ArgumentParser(description='Benchmark des modeles ML')
    parser.add_argument('--model', type=str, required=True,
                        choices=['car_detector', 'noisy_car_detector'],
                        help='Modele a analyser')
    parser.add_argument('--add-features', action='store_true',
                        help='Afficher les suggestions de nouvelles features')
    parser.add_argument('--optimized', action='store_true',
                        help='Utiliser les features optimisees (40 meilleures)')
    parser.add_argument('--output-dir', type=str, default='benchmark_results',
                        help='Dossier de sortie pour les figures')

    args = parser.parse_args()

    # Create output directory
    output_dir = PROJECT_ROOT / args.output_dir
    output_dir.mkdir(exist_ok=True)

    # Load data
    print_info(f"Chargement des features...")
    X, y, feature_names, df = load_features(args.model, use_optimized=args.optimized)

    # Noms pour fichiers et affichage
    model_names = {
        'car_detector': 'Detecteur Vehicule',
        'noisy_car_detector': 'Detecteur Vehicule Bruyant'
    }
    display_name = model_names.get(args.model, args.model)

    if args.optimized:
        file_label = f"{args.model}_optimized"
        display_label = f"{display_name} ({X.shape[1]} features optimisees)"
    else:
        file_label = f"{args.model}_all"
        display_label = f"{display_name} ({X.shape[1]} features)"

    print_header(f"BENCHMARK - {display_label.upper()}")
    print()

    # 1. Analyze features
    X_scaled, correlations = analyze_features(X, y, feature_names, display_label)

    # 2. Visualize clusters
    visualize_clusters(X, y, display_label, output_dir, file_label)

    # 3. Compare models
    results = compare_models(X, y, display_label, output_dir, file_label)

    # 4. Detect overfitting
    detect_overfitting(X, y, display_label, output_dir, file_label)

    # 5. Suggest new features
    if args.add_features:
        suggest_new_features()

    # Summary
    print_header("RESUME")
    print()

    best_model = results[0]
    mlp_current = next((r for r in results if 'MLP (current)' in r['Model']), None)

    print(f"Dataset: {X.shape[0]} echantillons, {X.shape[1]} features")
    print(f"Meilleur modele: {best_model['Model']} (F1={best_model['F1 Mean']:.3f})")

    if mlp_current:
        print(f"Neural Network actuel: F1={mlp_current['F1 Mean']:.3f}")

        if best_model['F1 Mean'] > mlp_current['F1 Mean'] + 0.01:
            print()
            print_warning("RECOMMANDATION: Utiliser un modele plus simple!")
            print_warning(f"  {best_model['Model']} performe mieux que le NN actuel")

    print()
    print_success(f"Resultats sauvegardes dans: {output_dir}")


if __name__ == "__main__":
    main()
