#!/usr/bin/env python3
"""
Entraînement du modèle NoisyCarDetector.

Usage:
    python -m models.noisy_car_detector.train              # Entraîner
    python -m models.noisy_car_detector.train --features 15  # Custom features
    python -m models.noisy_car_detector.train --no-plot    # Sans graphiques
"""

import argparse
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import joblib

from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import f1_score, classification_report, confusion_matrix
from imblearn.over_sampling import SMOTE

import tensorflow as tf
from tensorflow.keras import layers, models, regularizers

from config import get_settings
from shared import print_header, print_success, print_info, print_warning, print_error, Colors
from . import config

settings = get_settings()


def setup_gpu():
    """Configure TensorFlow GPU."""
    gpus = tf.config.list_physical_devices('GPU')
    if gpus:
        try:
            for gpu in gpus:
                tf.config.experimental.set_memory_growth(gpu, True)
            return f"GPU ({len(gpus)})", True
        except RuntimeError:
            pass
    return "CPU", False


def select_features(X: np.ndarray, y: np.ndarray, names: list, n: int) -> tuple:
    """Sélectionne les N meilleures features via Random Forest."""
    rf = RandomForestClassifier(n_estimators=100, random_state=42, n_jobs=-1)
    rf.fit(X, y)

    importance = pd.DataFrame({'name': names, 'score': rf.feature_importances_})
    importance = importance.sort_values('score', ascending=False)

    # Sauvegarder
    importance.to_csv(config.DATA_DIR / "feature_importance.csv", index=False)

    top = importance.head(n)['name'].tolist()
    print_info(f"Top {n} features sélectionnées")

    return top, [names.index(f) for f in top]


def create_model(n_features: int) -> tf.keras.Model:
    """Crée le modèle MLP."""
    model = models.Sequential([
        layers.Input(shape=(n_features,)),
        layers.Dense(64, activation='relu', kernel_regularizer=regularizers.l2(0.001)),
        layers.Dropout(0.3),
        layers.Dense(32, activation='relu', kernel_regularizer=regularizers.l2(0.001)),
        layers.Dropout(0.2),
        layers.Dense(1, activation='sigmoid')
    ])

    model.compile(
        optimizer=tf.keras.optimizers.Adam(learning_rate=0.001),
        loss='binary_crossentropy',
        metrics=['accuracy']
    )
    return model


def train(n_features: int = None, show_plot: bool = True):
    """Entraîne le modèle."""

    # Config
    device, has_gpu = setup_gpu()
    print_header(f"NoisyCarDetector Training [{device}]")

    if not config.FEATURES_CSV.exists():
        print_error("Features non extraites. Lancez d'abord:")
        print_info("  python -m models.noisy_car_detector.feature_extraction")
        return 1

    # Charger données
    df = pd.read_csv(config.FEATURES_CSV)
    print_info(f"Données: {len(df)} échantillons")

    meta_cols = ['nfile', 'label', 'reliability']
    feature_cols = [c for c in df.columns if c not in meta_cols]

    X = df[feature_cols].values
    y = df['label'].values

    # Distribution
    for lbl in [0, 1]:
        name = config.NEGATIVE_LABEL if lbl == 0 else config.POSITIVE_LABEL
        print_info(f"  {name}: {(y == lbl).sum()}")

    # Split 3-voies : train / val (EarlyStopping) / test (évaluation finale uniquement)
    # Le test set est hermétiquement isolé — EarlyStopping ne le voit jamais.
    X_trainval, X_test, y_trainval, y_test = train_test_split(
        X, y, test_size=settings.TEST_SIZE, random_state=42, stratify=y
    )
    X_train, X_val, y_train, y_val = train_test_split(
        X_trainval, y_trainval, test_size=0.2, random_state=42, stratify=y_trainval
    )
    print_info(f"Split: Train={len(X_train)} | Val={len(X_val)} | Test={len(X_test)}")

    # Sélection features sur le train set uniquement (pas de leakage)
    n_top = n_features or settings.TOP_FEATURES_COUNT
    top_features, indices = select_features(X_train, y_train, feature_cols, n_top)
    X_train = X_train[:, indices]
    X_val   = X_val[:, indices]
    X_test  = X_test[:, indices]

    # SMOTE uniquement sur le training set
    minority = min((y_train == 0).sum(), (y_train == 1).sum())
    k = min(settings.SMOTE_K_NEIGHBORS, minority - 1)
    k = max(1, k)

    smote_ok = False
    try:
        smote = SMOTE(k_neighbors=k, random_state=42)
        X_train, y_train = smote.fit_resample(X_train, y_train)
        print_info(f"SMOTE: {len(X_train)} échantillons (train)")
        smote_ok = True
    except Exception as e:
        print_warning(f"SMOTE échoué: {e}")

    # Standardisation — fit sur train uniquement
    scaler = StandardScaler()
    X_train = scaler.fit_transform(X_train)
    X_val   = scaler.transform(X_val)
    X_test  = scaler.transform(X_test)

    # Modèle
    model = create_model(X_train.shape[1])

    # Class weights — uniquement si SMOTE a échoué (évite la double compensation)
    if smote_ok:
        class_weights = None
    else:
        unique, counts = np.unique(y_train, return_counts=True)
        total = len(y_train)
        class_weights = {int(c): total / (len(unique) * count) for c, count in zip(unique, counts)}

    # Callbacks
    early_stop = tf.keras.callbacks.EarlyStopping(
        monitor='val_loss', patience=20, restore_best_weights=True
    )

    class Progress(tf.keras.callbacks.Callback):
        def on_epoch_end(self, epoch, logs=None):
            if (epoch + 1) % 10 == 0:
                print_info(f"Epoch {epoch+1}: acc={logs['accuracy']:.3f} val_acc={logs.get('val_accuracy', 0):.3f}")

    # Training — EarlyStopping sur le val set (jamais le test set)
    print_header("Training")
    history = model.fit(
        X_train, y_train,
        epochs=settings.TRAINING_EPOCHS,
        batch_size=settings.TRAINING_BATCH_SIZE,
        validation_data=(X_val, y_val),
        class_weight=class_weights,
        verbose=0,
        callbacks=[Progress(), early_stop]
    )

    # Évaluation
    print_header("Résultats")
    loss, acc = model.evaluate(X_test, y_test, verbose=0)
    y_pred = (model.predict(X_test, verbose=0) > 0.5).astype(int).flatten()
    f1 = f1_score(y_test, y_pred)

    print(f"\n  Accuracy: {acc*100:.2f}%")
    print(f"  F1 Score: {Colors.GREEN}{f1:.4f}{Colors.END}")
    print(f"  Loss:     {loss:.4f}\n")

    print(classification_report(y_test, y_pred,
          target_names=[config.NEGATIVE_LABEL, config.POSITIVE_LABEL]))

    cm = confusion_matrix(y_test, y_pred)
    print(f"  Confusion: TN={cm[0,0]} FP={cm[0,1]} FN={cm[1,0]} TP={cm[1,1]}")

    # Visualisation
    if show_plot:
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 4))

        ax1.plot(history.history['accuracy'], label='Train')
        ax1.plot(history.history['val_accuracy'], label='Val')
        ax1.set_title('Accuracy')
        ax1.legend()
        ax1.grid(True, alpha=0.3)

        ax2.plot(history.history['loss'], label='Train')
        ax2.plot(history.history['val_loss'], label='Val')
        ax2.set_title('Loss')
        ax2.legend()
        ax2.grid(True, alpha=0.3)

        plt.tight_layout()
        plt.savefig(config.DATA_DIR / "training_history.png", dpi=150)
        plt.show()

    # Sauvegarde
    print_header("Sauvegarde")
    config.ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)

    model.save(str(config.MODEL_PATH))
    joblib.dump(scaler, str(config.SCALER_PATH))
    with open(config.FEATURES_PATH, 'w') as f:
        f.write('\n'.join(top_features))

    print_success(f"Modèle:   {config.MODEL_PATH}")
    print_success(f"Scaler:   {config.SCALER_PATH}")
    print_success(f"Features: {config.FEATURES_PATH}")

    print(f"\n{Colors.GREEN}✓{Colors.END} Entraînement terminé (F1={f1:.4f})")
    return 0


def main():
    parser = argparse.ArgumentParser(description="Entraînement NoisyCarDetector")
    parser.add_argument('--features', '-n', type=int, default=None,
                        help=f"Nombre de features (défaut: {settings.TOP_FEATURES_COUNT})")
    parser.add_argument('--no-plot', action='store_true',
                        help="Désactiver les graphiques")

    args = parser.parse_args()
    return train(n_features=args.features, show_plot=not args.no_plot)


if __name__ == "__main__":
    try:
        exit(main())
    except KeyboardInterrupt:
        print("\nAnnulé")
        exit(130)
