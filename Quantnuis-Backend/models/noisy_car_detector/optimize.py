#!/usr/bin/env python3
"""
================================================================================
              OPTIMISATION HYPERPARAMÈTRES - VOITURE BRUYANTE
================================================================================

Utilise Optuna pour trouver les meilleurs hyperparamètres du modèle.

Usage:
    python -m models.noisy_car_detector.optimize
    python -m models.noisy_car_detector.optimize --trials 50

================================================================================
"""

import os
import sys
import argparse
import warnings
warnings.filterwarnings('ignore')

# Désactiver les logs TensorFlow
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'

import numpy as np
import pandas as pd
import optuna
from optuna.samplers import TPESampler

from sklearn.model_selection import StratifiedKFold
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import f1_score
from imblearn.over_sampling import SMOTE

import tensorflow as tf
tf.get_logger().setLevel('ERROR')
from tensorflow.keras import layers, models, regularizers

from config import get_settings
from shared import print_header, print_success, print_info, print_warning, Colors
from . import config

settings = get_settings()


def load_data():
    """Charge les données."""
    df = pd.read_csv(config.FEATURES_CSV)
    meta_cols = ['nfile', 'label', 'reliability']
    feature_cols = [c for c in df.columns if c not in meta_cols]
    X = df[feature_cols].values
    y = df['label'].values
    return X, y, feature_cols


def select_features(X, y, feature_cols, n_features):
    """Sélectionne les N meilleures features."""
    rf = RandomForestClassifier(n_estimators=100, random_state=42, n_jobs=-1)
    rf.fit(X, y)

    importance = pd.DataFrame({
        'Feature': feature_cols,
        'Importance': rf.feature_importances_
    }).sort_values('Importance', ascending=False)

    top_features = importance['Feature'].head(n_features).tolist()
    indices = [feature_cols.index(f) for f in top_features]

    return X[:, indices], top_features


def create_model(n_features, layer1_size, layer2_size, dropout1, dropout2, l2_reg, learning_rate):
    """Crée un modèle avec les hyperparamètres donnés."""
    model = models.Sequential([
        layers.Input(shape=(n_features,)),
        layers.Dense(layer1_size, activation='relu',
                     kernel_regularizer=regularizers.l2(l2_reg)),
        layers.Dropout(dropout1),
        layers.Dense(layer2_size, activation='relu',
                     kernel_regularizer=regularizers.l2(l2_reg)),
        layers.Dropout(dropout2),
        layers.Dense(1, activation='sigmoid')
    ])

    model.compile(
        optimizer=tf.keras.optimizers.Adam(learning_rate=learning_rate),
        loss='binary_crossentropy',
        metrics=['accuracy']
    )

    return model


def objective(trial):
    """Fonction objectif pour Optuna."""

    # Hyperparamètres à optimiser
    n_features = trial.suggest_int('n_features', 8, 30)
    layer1_size = trial.suggest_categorical('layer1_size', [32, 64, 96, 128])
    layer2_size = trial.suggest_categorical('layer2_size', [16, 32, 48, 64])
    dropout1 = trial.suggest_float('dropout1', 0.1, 0.5)
    dropout2 = trial.suggest_float('dropout2', 0.1, 0.4)
    l2_reg = trial.suggest_float('l2_reg', 1e-5, 1e-2, log=True)
    learning_rate = trial.suggest_float('learning_rate', 1e-4, 1e-2, log=True)
    batch_size = trial.suggest_categorical('batch_size', [8, 16, 32])
    smote_k = trial.suggest_int('smote_k', 2, 5)

    # Charger et préparer les données
    X, y, feature_cols = load_data()
    X_selected, _ = select_features(X, y, feature_cols, n_features)

    # Validation croisée stratifiée
    kfold = StratifiedKFold(n_splits=3, shuffle=True, random_state=42)
    f1_scores = []

    for train_idx, val_idx in kfold.split(X_selected, y):
        X_train, X_val = X_selected[train_idx], X_selected[val_idx]
        y_train, y_val = y[train_idx], y[val_idx]

        # SMOTE
        minority_count = min(np.sum(y_train == 0), np.sum(y_train == 1))
        k_neighbors = min(smote_k, minority_count - 1)
        k_neighbors = max(1, k_neighbors)

        try:
            smote = SMOTE(k_neighbors=k_neighbors, random_state=42)
            X_train_res, y_train_res = smote.fit_resample(X_train, y_train)
        except:
            X_train_res, y_train_res = X_train, y_train

        # Standardisation
        scaler = StandardScaler()
        X_train_scaled = scaler.fit_transform(X_train_res)
        X_val_scaled = scaler.transform(X_val)

        # Modèle
        model = create_model(
            n_features, layer1_size, layer2_size,
            dropout1, dropout2, l2_reg, learning_rate
        )

        # Class weights
        unique, counts = np.unique(y_train_res, return_counts=True)
        total = len(y_train_res)
        class_weights = {int(c): total / (len(unique) * count) for c, count in zip(unique, counts)}

        # Entraînement
        early_stop = tf.keras.callbacks.EarlyStopping(
            monitor='val_loss', patience=10, restore_best_weights=True
        )

        model.fit(
            X_train_scaled, y_train_res,
            epochs=50,
            batch_size=batch_size,
            validation_data=(X_val_scaled, y_val),
            class_weight=class_weights,
            callbacks=[early_stop],
            verbose=0
        )

        # Évaluation
        y_pred = (model.predict(X_val_scaled, verbose=0) > 0.5).astype(int).flatten()
        f1 = f1_score(y_val, y_pred)
        f1_scores.append(f1)

        # Libérer mémoire
        del model
        tf.keras.backend.clear_session()

    return np.mean(f1_scores)


def optimize(n_trials=30):
    """Lance l'optimisation."""

    print_header("Optimisation Hyperparamètres")
    print_info(f"Nombre d'essais: {n_trials}")
    print_info("Métrique: F1 Score (validation croisée 3-fold)")
    print()

    # Créer l'étude Optuna
    study = optuna.create_study(
        direction='maximize',
        sampler=TPESampler(seed=42),
        study_name='noisy_car_detector'
    )

    # Callback pour afficher la progression
    def callback(study, trial):
        if trial.number % 5 == 0:
            print(f"  Trial {trial.number}: F1={trial.value:.4f} (Best: {study.best_value:.4f})")

    # Lancer l'optimisation
    study.optimize(objective, n_trials=n_trials, callbacks=[callback], show_progress_bar=True)

    # Résultats
    print_header("Meilleurs Hyperparamètres")

    best = study.best_params
    print(f"""
  {Colors.GREEN}F1 Score: {study.best_value:.4f}{Colors.END}

  {Colors.BOLD}Architecture:{Colors.END}
    • Features:     {best['n_features']}
    • Layer 1:      {best['layer1_size']} neurones
    • Layer 2:      {best['layer2_size']} neurones
    • Dropout 1:    {best['dropout1']:.2f}
    • Dropout 2:    {best['dropout2']:.2f}
    • L2 Reg:       {best['l2_reg']:.6f}

  {Colors.BOLD}Entraînement:{Colors.END}
    • Learning Rate: {best['learning_rate']:.6f}
    • Batch Size:    {best['batch_size']}
    • SMOTE k:       {best['smote_k']}
    """)

    # Sauvegarder les résultats
    results_path = config.DATA_DIR / "optimization_results.csv"
    study.trials_dataframe().to_csv(results_path, index=False)
    print_success(f"Résultats sauvegardés: {results_path}")

    # Afficher les 5 meilleurs essais
    print_header("Top 5 Essais")
    df = study.trials_dataframe().sort_values('value', ascending=False).head(5)
    for i, (_, row) in enumerate(df.iterrows(), 1):
        print(f"  {i}. F1={row['value']:.4f} | features={int(row['params_n_features'])} | "
              f"L1={int(row['params_layer1_size'])} | L2={int(row['params_layer2_size'])}")

    return study.best_params, study.best_value


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Optimisation hyperparamètres NoisyCarDetector")
    parser.add_argument('--trials', type=int, default=30, help="Nombre d'essais (défaut: 30)")
    args = parser.parse_args()

    try:
        optimize(n_trials=args.trials)
    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}[!]{Colors.END} Annulé")
