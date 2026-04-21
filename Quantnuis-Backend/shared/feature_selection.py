#!/usr/bin/env python3
"""
================================================================================
                    SELECTION DE FEATURES
================================================================================

Sélectionne les meilleures features pour améliorer le clustering et les modèles.

Méthodes:
1. Corrélation avec le label (importance univariée)
2. Élimination des features redondantes (corrélation inter-features)
3. Variance minimale

Usage:
    python -m shared.feature_selection --model car_detector --top 50
    python -m shared.feature_selection --model car_detector --analyze

================================================================================
"""

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler
from sklearn.feature_selection import mutual_info_classif, SelectKBest, f_classif

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from shared import print_header, print_info, print_success, print_warning


MODELS_CONFIG = {
    'car_detector': {
        'features_csv': PROJECT_ROOT / 'data' / 'car_detector' / 'features_all.csv',
        'optimized_csv': PROJECT_ROOT / 'data' / 'car_detector' / 'features_optimized.csv',
    },
    'noisy_car_detector': {
        'features_csv': PROJECT_ROOT / 'data' / 'noisy_car_detector' / 'features_all.csv',
        'optimized_csv': PROJECT_ROOT / 'data' / 'noisy_car_detector' / 'features_optimized.csv',
    }
}


def load_data(model_name: str):
    """Charge les données."""
    config = MODELS_CONFIG[model_name]
    df = pd.read_csv(config['features_csv'])

    # Séparer features et labels
    meta_cols = ['nfile', 'label', 'reliability', 'file', 'filename']
    feature_cols = [c for c in df.columns if c not in meta_cols]

    X = df[feature_cols].values
    y = df['label'].values
    X = np.nan_to_num(X, nan=0.0, posinf=0.0, neginf=0.0)

    return X, y, feature_cols, df


def compute_correlations(X: np.ndarray, y: np.ndarray, feature_names: list) -> list:
    """Calcule la corrélation de chaque feature avec le label."""
    correlations = []
    for i, fname in enumerate(feature_names):
        corr = np.corrcoef(X[:, i], y)[0, 1]
        if np.isnan(corr):
            corr = 0.0
        correlations.append((fname, abs(corr), i))

    correlations.sort(key=lambda x: x[1], reverse=True)
    return correlations


def remove_redundant_features(X: np.ndarray, feature_names: list, threshold: float = 0.95) -> list:
    """
    Supprime les features fortement corrélées entre elles.

    Garde la première feature de chaque groupe de features corrélées.
    """
    n_features = X.shape[1]
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    # Matrice de corrélation
    corr_matrix = np.corrcoef(X_scaled.T)

    # Trouver les features à supprimer
    to_remove = set()
    for i in range(n_features):
        if i in to_remove:
            continue
        for j in range(i + 1, n_features):
            if j in to_remove:
                continue
            if abs(corr_matrix[i, j]) > threshold:
                to_remove.add(j)

    # Features à garder
    keep_indices = [i for i in range(n_features) if i not in to_remove]
    keep_names = [feature_names[i] for i in keep_indices]

    return keep_names, len(to_remove)


def select_top_features(
    X: np.ndarray,
    y: np.ndarray,
    feature_names: list,
    n_features: int = 50,
    remove_redundant: bool = True,
    redundancy_threshold: float = 0.90
) -> tuple:
    """
    Sélectionne les meilleures features.

    1. Calcule la corrélation avec le label
    2. Optionnellement supprime les features redondantes
    3. Garde les top N features

    Retourne:
        tuple: (selected_features, feature_scores)
    """
    # Étape 1: Corrélation avec le label
    correlations = compute_correlations(X, y, feature_names)

    # Créer un mapping nom -> score
    feature_scores = {fname: corr for fname, corr, _ in correlations}

    if remove_redundant:
        # Étape 2: Supprimer les features redondantes parmi les top 2*n_features
        top_candidates = [fname for fname, _, _ in correlations[:min(n_features * 2, len(correlations))]]
        candidate_indices = [feature_names.index(f) for f in top_candidates]
        X_candidates = X[:, candidate_indices]

        non_redundant, n_removed = remove_redundant_features(
            X_candidates, top_candidates, threshold=redundancy_threshold
        )
        print_info(f"{n_removed} features redondantes supprimées")

        # Garder les top N parmi les non-redondantes
        selected = []
        for fname, corr, _ in correlations:
            if fname in non_redundant:
                selected.append(fname)
            if len(selected) >= n_features:
                break
    else:
        # Juste garder les top N
        selected = [fname for fname, _, _ in correlations[:n_features]]

    return selected, feature_scores


def analyze_features(model_name: str):
    """Analyse les features et affiche les statistiques."""
    print_header(f"ANALYSE DES FEATURES - {model_name.upper()}")

    X, y, feature_names, df = load_data(model_name)

    print_info(f"Échantillons: {X.shape[0]}")
    print_info(f"Features: {X.shape[1]}")

    # Corrélations
    correlations = compute_correlations(X, y, feature_names)

    print_header("TOP 20 FEATURES (corrélation avec label)")
    for i, (fname, corr, _) in enumerate(correlations[:20], 1):
        print(f"  {i:2d}. {fname:<35} {corr:.3f}")

    # Catégories de features
    print_header("CATEGORIES DE FEATURES")

    categories = {
        'MFCC base': [f for f in feature_names if f.startswith('mfcc_') and 'delta' not in f],
        'Delta MFCC': [f for f in feature_names if 'delta_mfcc' in f or 'delta2_mfcc' in f],
        'Spectral': [f for f in feature_names if 'spectral' in f],
        'Mel bands': [f for f in feature_names if f.startswith('mel_')],
        'Freq energy': [f for f in feature_names if 'freq_energy' in f or 'freq_ratio' in f],
        'Onset': [f for f in feature_names if 'onset' in f],
        'Autres': []
    }

    # Classer les autres
    categorized = set()
    for cat_features in categories.values():
        categorized.update(cat_features)
    categories['Autres'] = [f for f in feature_names if f not in categorized]

    for cat_name, cat_features in categories.items():
        if not cat_features:
            continue

        avg_corr = np.mean([abs(np.corrcoef(X[:, feature_names.index(f)], y)[0, 1])
                           for f in cat_features if feature_names.index(f) < X.shape[1]])
        print(f"  {cat_name:<15} {len(cat_features):3d} features, corr moyenne: {avg_corr:.3f}")

    # Recommandation
    print_header("RECOMMANDATION")

    # Compter les nouvelles features véhicule dans le top 50
    vehicle_features = ['low_freq_energy', 'very_low_freq_energy', 'mid_freq_energy',
                        'high_freq_energy', 'low_freq_ratio', 'low_high_ratio']
    vehicle_in_top50 = sum(1 for f, _, _ in correlations[:50] if f in vehicle_features)
    delta_in_top50 = sum(1 for f, _, _ in correlations[:50] if 'delta' in f)

    print(f"  Features véhicule dans top 50: {vehicle_in_top50}/6")
    print(f"  Delta MFCC dans top 50: {delta_in_top50}")

    if X.shape[1] > 100 and X.shape[0] < 500:
        print_warning(f"  Ratio features/échantillons élevé ({X.shape[1]}/{X.shape[0]})")
        print_info("  Recommandé: sélectionner 30-50 features")


def create_optimized_dataset(model_name: str, n_features: int = 50):
    """Crée un dataset avec les features optimisées (meilleures features sélectionnées)."""
    print_header(f"OPTIMISATION DES FEATURES - {model_name.upper()}")

    X, y, feature_names, df = load_data(model_name)
    config = MODELS_CONFIG[model_name]

    print_info(f"Features originales: {len(feature_names)}")

    # Sélectionner les features
    selected, scores = select_top_features(
        X, y, feature_names,
        n_features=n_features,
        remove_redundant=True,
        redundancy_threshold=0.90
    )

    print_info(f"Features optimisées: {len(selected)}")

    # Afficher les features sélectionnées
    print_header("FEATURES OPTIMISEES")
    for i, fname in enumerate(selected[:20], 1):
        print(f"  {i:2d}. {fname:<35} (corr: {scores[fname]:.3f})")
    if len(selected) > 20:
        print(f"  ... et {len(selected) - 20} autres")

    # Créer le nouveau dataset
    meta_cols = ['nfile', 'label']
    if 'reliability' in df.columns:
        meta_cols.append('reliability')

    df_optimized = df[meta_cols + selected].copy()

    # Sauvegarder
    df_optimized.to_csv(config['optimized_csv'], index=False)
    print_success(f"Sauvegardé: {config['optimized_csv']}")

    # Sauvegarder aussi la liste des features
    features_list_path = config['optimized_csv'].parent / 'optimized_features.txt'
    with open(features_list_path, 'w') as f:
        f.write('\n'.join(selected))
    print_info(f"Liste des features: {features_list_path}")

    return selected


def main():
    parser = argparse.ArgumentParser(description='Optimisation des features')
    parser.add_argument('--model', type=str, required=True,
                        choices=['car_detector', 'noisy_car_detector'])
    parser.add_argument('--analyze', action='store_true',
                        help='Analyser les features sans optimiser')
    parser.add_argument('--top', type=int, default=50,
                        help='Nombre de features à garder')

    args = parser.parse_args()

    if args.analyze:
        analyze_features(args.model)
    else:
        create_optimized_dataset(args.model, n_features=args.top)


if __name__ == "__main__":
    main()
