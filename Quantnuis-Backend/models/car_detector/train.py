#!/usr/bin/env python3
"""
================================================================================
                    ENTRAÎNEMENT - DÉTECTION VOITURE
================================================================================

Entraîne le modèle de classification pour détecter si un audio contient
une voiture ou non.

Pipeline :
    1. Chargement des features depuis le CSV
    2. Sélection des meilleures features (Top N du Random Forest)
    3. Data Augmentation avec SMOTE
    4. Split Train/Test (80%/20%)
    5. Standardisation des données
    6. Création du modèle de neurones
    7. Entraînement
    8. Évaluation et visualisation
    9. Sauvegarde

Usage:
    python -m models.car_detector.train

================================================================================
"""

import os
import sys
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import joblib

from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import RandomForestClassifier
from imblearn.over_sampling import SMOTE

import tensorflow as tf
from tensorflow.keras import layers, models, regularizers

from config import get_settings
from shared import (
    print_header, print_success, print_info, 
    print_warning, print_error, Colors
)
from . import config

settings = get_settings()


def setup_gpu():
    """Configure TensorFlow pour utiliser le GPU si disponible."""
    gpus = tf.config.list_physical_devices('GPU')
    
    if gpus:
        try:
            for gpu in gpus:
                tf.config.experimental.set_memory_growth(gpu, True)
            return f"GPU CUDA ({len(gpus)} device(s))", [g.name for g in gpus]
        except RuntimeError as e:
            return f"GPU (erreur: {e})", []
    
    return "CPU (pas de GPU détecté)", []


def analyze_feature_importance(X: np.ndarray, y: np.ndarray, 
                               feature_names: list, n_top: int = 12) -> list:
    """
    Analyse l'importance des features avec Random Forest.
    
    Paramètres:
        X: Matrice des features
        y: Labels
        feature_names: Noms des features
        n_top: Nombre de features à sélectionner
    
    Retourne:
        list: Top N features les plus importantes
    """
    print_info("Analyse de l'importance des features...")
    
    rf = RandomForestClassifier(n_estimators=100, random_state=42, n_jobs=-1)
    rf.fit(X, y)
    
    # Trier par importance
    importance = pd.DataFrame({
        'Feature': feature_names,
        'Importance': rf.feature_importances_
    }).sort_values('Importance', ascending=False)
    
    # Sauvegarder l'analyse
    importance_path = config.DATA_DIR / "feature_importance.csv"
    importance.to_csv(importance_path, index=False)
    print_success(f"Importance sauvegardée: {importance_path}")
    
    top_features = importance['Feature'].head(n_top).tolist()
    
    print_info(f"Top {n_top} features:")
    for i, feat in enumerate(top_features, 1):
        score = importance[importance['Feature'] == feat]['Importance'].values[0]
        print(f"    {i:>2}. {feat}: {score:.4f}")
    
    return top_features


def create_model(n_features: int) -> tf.keras.Model:
    """
    Crée le modèle de réseau de neurones.
    
    Architecture :
        Input (n_features) → Dense 64 → Dropout → Dense 32 → Dropout → Output 1
    
    Paramètres:
        n_features: Nombre de features en entrée
    
    Retourne:
        tf.keras.Model: Modèle compilé
    """
    model = models.Sequential([
        layers.Input(shape=(n_features,)),
        
        # Première couche cachée
        layers.Dense(64, activation='relu', 
                     kernel_regularizer=regularizers.l2(0.001)),
        layers.Dropout(0.3),
        
        # Deuxième couche cachée
        layers.Dense(32, activation='relu',
                     kernel_regularizer=regularizers.l2(0.001)),
        layers.Dropout(0.2),
        
        # Couche de sortie
        layers.Dense(1, activation='sigmoid')
    ])
    
    model.compile(
        optimizer=tf.keras.optimizers.Adam(learning_rate=0.001),
        loss='binary_crossentropy',
        metrics=['accuracy']
    )
    
    return model


def train_car_detector():
    """
    Fonction principale d'entraînement du modèle de détection voiture.
    """
    
    # ==========================================================================
    # CONFIGURATION GPU
    # ==========================================================================
    
    print_header("Configuration Hardware")
    device_type, gpu_info = setup_gpu()
    
    print_info(f"TensorFlow version: {tf.__version__}")
    if "GPU" in device_type:
        print_success(f"Device: {device_type}")
    else:
        print_warning(f"Device: {device_type}")
    
    # ==========================================================================
    # CHARGEMENT DES DONNÉES
    # ==========================================================================
    
    print_header("Chargement des Données")
    
    if not config.FEATURES_CSV.exists():
        print_error(f"Fichier non trouvé: {config.FEATURES_CSV}")
        print_info("Lancez d'abord: python -m models.car_detector.feature_extraction")
        return
    
    df = pd.read_csv(config.FEATURES_CSV)
    print_info(f"{len(df)} échantillons chargés")
    
    # ==========================================================================
    # PRÉPARATION DES FEATURES
    # ==========================================================================
    
    print_header("Préparation des Features")
    
    # Colonnes de features (exclure métadonnées)
    meta_cols = ['nfile', 'label', 'reliability']
    feature_cols = [c for c in df.columns if c not in meta_cols]
    
    X = df[feature_cols].values
    y = df['label'].values
    
    # Convertir les labels si nécessaire (1, 2 -> 0, 1)
    unique_labels = np.unique(y)
    print_info(f"Labels uniques: {unique_labels}")
    
    if 2 in unique_labels:
        y = np.where(y == 1, 0, 1)
        print_info("Labels convertis: 1→0, 2→1")
    
    # ==========================================================================
    # SÉLECTION DES MEILLEURES FEATURES
    # ==========================================================================
    
    print_header("Sélection des Features")
    
    n_top = settings.TOP_FEATURES_COUNT
    top_features = analyze_feature_importance(X, y, feature_cols, n_top)
    
    # Filtrer les features
    feature_indices = [feature_cols.index(f) for f in top_features]
    X = X[:, feature_indices]
    
    print_success(f"{len(top_features)} features sélectionnées")
    
    # ==========================================================================
    # DATA AUGMENTATION (SMOTE)
    # ==========================================================================
    
    print_header("Data Augmentation (SMOTE)")
    
    print_info(f"Taille avant: {X.shape[0]} échantillons")
    
    try:
        smote = SMOTE(k_neighbors=settings.SMOTE_K_NEIGHBORS, random_state=42)
        X_resampled, y_resampled = smote.fit_resample(X, y)
        
        print_success(f"Taille après: {X_resampled.shape[0]} échantillons")
        print_info(f"+{X_resampled.shape[0] - X.shape[0]} données synthétiques")
        
        unique, counts = np.unique(y_resampled, return_counts=True)
        for label, count in zip(unique, counts):
            label_name = config.NEGATIVE_LABEL if label == 0 else config.POSITIVE_LABEL
            print_info(f"Classe {label} ({label_name}): {count}")
    except Exception as e:
        print_warning(f"SMOTE échoué: {e}")
        X_resampled, y_resampled = X, y
    
    # ==========================================================================
    # SPLIT TRAIN/TEST
    # ==========================================================================
    
    print_header("Split Train/Test")
    
    X_train, X_test, y_train, y_test = train_test_split(
        X_resampled, y_resampled,
        test_size=settings.TEST_SIZE,
        random_state=42,
        stratify=y_resampled
    )
    
    print_info(f"Train: {X_train.shape[0]} échantillons")
    print_info(f"Test:  {X_test.shape[0]} échantillons")
    
    # ==========================================================================
    # STANDARDISATION
    # ==========================================================================
    
    print_header("Standardisation")
    
    scaler = StandardScaler()
    X_train = scaler.fit_transform(X_train)
    X_test = scaler.transform(X_test)
    
    print_success("Données standardisées (μ=0, σ=1)")
    
    # ==========================================================================
    # CRÉATION DU MODÈLE
    # ==========================================================================
    
    print_header("Création du Modèle")
    
    model = create_model(X_train.shape[1])
    model.summary()
    
    # ==========================================================================
    # ENTRAÎNEMENT
    # ==========================================================================
    
    print_header("Entraînement")
    
    class ProgressCallback(tf.keras.callbacks.Callback):
        def on_epoch_end(self, epoch, logs=None):
            if (epoch + 1) % 10 == 0:
                acc = logs.get('accuracy', 0) * 100
                val_acc = logs.get('val_accuracy', 0) * 100
                print(f"    Epoch {epoch+1}/{settings.TRAINING_EPOCHS} - "
                      f"Acc: {acc:.1f}% - Val Acc: {val_acc:.1f}%")
    
    history = model.fit(
        X_train, y_train,
        epochs=settings.TRAINING_EPOCHS,
        batch_size=settings.TRAINING_BATCH_SIZE,
        validation_data=(X_test, y_test),
        verbose=0,
        callbacks=[ProgressCallback()]
    )
    
    # ==========================================================================
    # ÉVALUATION
    # ==========================================================================
    
    print_header("Résultats")
    
    loss, accuracy = model.evaluate(X_test, y_test, verbose=0)
    
    print(f"\n  {Colors.BOLD}Performance finale:{Colors.END}")
    print(f"    • Précision: {Colors.GREEN}{accuracy*100:.2f}%{Colors.END}")
    print(f"    • Erreur:    {loss:.4f}")
    
    if accuracy >= 0.9:
        print(f"\n  {Colors.GREEN}✓ Excellent !{Colors.END}")
    elif accuracy >= 0.75:
        print(f"\n  {Colors.YELLOW}⚠ Bon, mais améliorable{Colors.END}")
    else:
        print(f"\n  {Colors.RED}✗ Besoin de plus de données{Colors.END}")
    
    # ==========================================================================
    # VISUALISATION
    # ==========================================================================
    
    print_header("Visualisation")
    
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    
    axes[0].plot(history.history['accuracy'], label='Train', linewidth=2)
    axes[0].plot(history.history['val_accuracy'], label='Validation', linewidth=2)
    axes[0].set_title('Précision - Détection Voiture', fontweight='bold')
    axes[0].set_xlabel('Epoch')
    axes[0].set_ylabel('Accuracy')
    axes[0].legend()
    axes[0].grid(True, alpha=0.3)
    
    axes[1].plot(history.history['loss'], label='Train', linewidth=2)
    axes[1].plot(history.history['val_loss'], label='Validation', linewidth=2)
    axes[1].set_title('Erreur (Loss)', fontweight='bold')
    axes[1].set_xlabel('Epoch')
    axes[1].set_ylabel('Loss')
    axes[1].legend()
    axes[1].grid(True, alpha=0.3)
    
    plt.tight_layout()
    
    history_path = config.DATA_DIR / "training_history.png"
    plt.savefig(history_path, dpi=150, bbox_inches='tight')
    print_success(f"Courbes sauvegardées: {history_path}")
    plt.show()
    
    # ==========================================================================
    # SAUVEGARDE
    # ==========================================================================
    
    print_header("Sauvegarde")
    
    # Créer le dossier artifacts
    config.ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    
    # Sauvegarder le modèle
    model.save(str(config.MODEL_PATH))
    print_success(f"Modèle: {config.MODEL_PATH}")
    
    # Sauvegarder le scaler
    joblib.dump(scaler, str(config.SCALER_PATH))
    print_success(f"Scaler: {config.SCALER_PATH}")
    
    # Sauvegarder la liste des features
    with open(config.FEATURES_PATH, 'w') as f:
        f.write('\n'.join(top_features))
    print_success(f"Features: {config.FEATURES_PATH}")
    
    # ==========================================================================
    # RÉSUMÉ
    # ==========================================================================
    
    print_header("Résumé")
    
    print(f"""
  {Colors.BOLD}Entraînement terminé - Détection Voiture{Colors.END}
  
  • Données originales:    {X.shape[0]} échantillons
  • Après SMOTE:           {X_resampled.shape[0]} échantillons
  • Features utilisées:    {len(top_features)}
  • Précision finale:      {Colors.GREEN}{accuracy*100:.2f}%{Colors.END}
  
  {Colors.BOLD}Fichiers générés:{Colors.END}
  • {config.MODEL_PATH}
  • {config.SCALER_PATH}
  • {config.FEATURES_PATH}
  
  {Colors.GREEN}✓{Colors.END} Prêt pour la production !
    """)


if __name__ == "__main__":
    try:
        train_car_detector()
    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}[!]{Colors.END} Annulé")
    except Exception as e:
        print_error(str(e))
        raise
