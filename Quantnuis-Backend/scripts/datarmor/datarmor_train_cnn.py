#!/usr/bin/env python3
"""
=============================================================================
  ALL-IN-ONE: Train CNN sur mel-spectrogrammes (datarmor, CPU 56 cores)
=============================================================================

Charge les segments bruyants + normaux, cree les spectrogrammes,
entraine un CNN en 5-fold CV, et exporte le meilleur modele.

Usage:
    python -u datarmor_train_cnn.py
    python -u datarmor_train_cnn.py --epochs 50 --batch-size 64
    python -u datarmor_train_cnn.py --bruyants segments_bruyants_v2/ --normaux segments_normaux/

Prerequis:
    pip install tensorflow librosa soundfile scikit-learn pandas numpy
=============================================================================
"""

import os
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "2"

import sys
import warnings
warnings.filterwarnings("ignore")

import numpy as np
import pandas as pd
import argparse
import json
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor, as_completed

DATARMOR_WORK = "/home4/datahome/gdgheras/"
SR = 22050
DURATION = 4.0
N_MELS = 128
HOP_LENGTH = 512
N_FFT = 2048


# =============================================================================
#  CHARGEMENT DES SPECTROGRAMMES
# =============================================================================

def load_one_spectrogram(args):
    """Charge un WAV et retourne son mel-spectrogramme."""
    import warnings
    warnings.filterwarnings("ignore")
    import librosa

    filepath, label = args
    try:
        y, sr = librosa.load(str(filepath), sr=SR, duration=DURATION)

        target_len = int(SR * DURATION)
        if len(y) < target_len:
            y = np.pad(y, (0, target_len - len(y)), mode='constant')
        else:
            y = y[:target_len]

        y = librosa.util.normalize(y)

        mel = librosa.feature.melspectrogram(
            y=y, sr=sr, n_mels=N_MELS, n_fft=N_FFT, hop_length=HOP_LENGTH
        )
        mel_db = librosa.power_to_db(mel, ref=np.max)

        return mel_db, label, Path(filepath).name
    except Exception:
        return None, label, Path(filepath).name


def load_all_spectrograms(bruyants_dir, normaux_dir, max_per_class=None, workers=48):
    """Charge tous les spectrogrammes en parallele."""
    bruyants_dir = Path(bruyants_dir)
    normaux_dir = Path(normaux_dir)

    # Lister les fichiers
    bruyant_files = sorted(bruyants_dir.glob("*.wav")) + sorted(bruyants_dir.glob("*.WAV"))
    normal_files = sorted(normaux_dir.glob("*.wav")) + sorted(normaux_dir.glob("*.WAV"))

    print(f"  Fichiers bruyants: {len(bruyant_files)}")
    print(f"  Fichiers normaux: {len(normal_files)}")

    # Limiter si demande
    if max_per_class:
        rng = np.random.RandomState(42)
        if len(bruyant_files) > max_per_class:
            indices = rng.choice(len(bruyant_files), size=max_per_class, replace=False)
            bruyant_files = [bruyant_files[i] for i in sorted(indices)]
        if len(normal_files) > max_per_class:
            indices = rng.choice(len(normal_files), size=max_per_class, replace=False)
            normal_files = [normal_files[i] for i in sorted(indices)]
        print(f"  Apres limitation: {len(bruyant_files)} bruyants, {len(normal_files)} normaux")

    # Equilibrer les classes
    n_min = min(len(bruyant_files), len(normal_files))
    rng = np.random.RandomState(42)
    if len(bruyant_files) > n_min:
        indices = rng.choice(len(bruyant_files), size=n_min, replace=False)
        bruyant_files = [bruyant_files[i] for i in sorted(indices)]
    if len(normal_files) > n_min:
        indices = rng.choice(len(normal_files), size=n_min, replace=False)
        normal_files = [normal_files[i] for i in sorted(indices)]

    print(f"  Equilibre: {len(bruyant_files)} bruyants, {len(normal_files)} normaux")

    # Preparer les taches
    tasks = [(str(f), 1) for f in bruyant_files] + [(str(f), 0) for f in normal_files]
    rng.shuffle(tasks)

    # Charger en parallele
    spectrograms = []
    labels = []
    done = 0
    errors = 0

    with ProcessPoolExecutor(max_workers=workers) as executor:
        futures = {executor.submit(load_one_spectrogram, t): t for t in tasks}
        for future in as_completed(futures):
            mel, label, fname = future.result()
            done += 1
            if mel is not None:
                spectrograms.append(mel)
                labels.append(label)
            else:
                errors += 1

            if done % 1000 == 0 or done == len(tasks):
                print(f"    [{done}/{len(tasks)}] {len(spectrograms)} ok, {errors} erreurs",
                      flush=True)

    X = np.array(spectrograms)[..., np.newaxis]  # (N, n_mels, time, 1)
    y = np.array(labels)

    # Normaliser
    X_mean, X_std = X.mean(), X.std()
    X = (X - X_mean) / (X_std + 1e-8)

    return X, y, float(X_mean), float(X_std)


# =============================================================================
#  MODELES CNN
# =============================================================================

def build_cnn(input_shape):
    """CNN optimise pour classification audio sur spectrogrammes."""
    import tensorflow as tf
    from tensorflow import keras

    model = keras.Sequential([
        # Block 1
        keras.layers.Conv2D(32, (3, 3), padding='same', input_shape=input_shape),
        keras.layers.BatchNormalization(),
        keras.layers.Activation('relu'),
        keras.layers.MaxPooling2D((2, 2)),
        keras.layers.Dropout(0.2),

        # Block 2
        keras.layers.Conv2D(64, (3, 3), padding='same'),
        keras.layers.BatchNormalization(),
        keras.layers.Activation('relu'),
        keras.layers.MaxPooling2D((2, 2)),
        keras.layers.Dropout(0.2),

        # Block 3
        keras.layers.Conv2D(128, (3, 3), padding='same'),
        keras.layers.BatchNormalization(),
        keras.layers.Activation('relu'),
        keras.layers.MaxPooling2D((2, 2)),
        keras.layers.Dropout(0.3),

        # Block 4
        keras.layers.Conv2D(256, (3, 3), padding='same'),
        keras.layers.BatchNormalization(),
        keras.layers.Activation('relu'),
        keras.layers.GlobalAveragePooling2D(),
        keras.layers.Dropout(0.4),

        # Dense
        keras.layers.Dense(128, activation='relu'),
        keras.layers.BatchNormalization(),
        keras.layers.Dropout(0.5),
        keras.layers.Dense(1, activation='sigmoid'),
    ])

    model.compile(
        optimizer=keras.optimizers.Adam(learning_rate=0.001),
        loss='binary_crossentropy',
        metrics=['accuracy']
    )

    return model


# =============================================================================
#  ENTRAINEMENT
# =============================================================================

def train_fold(X_train, y_train, X_val, y_val, input_shape, epochs, batch_size, fold_num):
    """Entraine un fold et retourne les metriques."""
    import tensorflow as tf
    from tensorflow import keras

    tf.random.set_seed(42 + fold_num)

    model = build_cnn(input_shape)

    # Class weights
    n_pos = (y_train == 1).sum()
    n_neg = (y_train == 0).sum()
    class_weight = {0: len(y_train) / (2 * n_neg), 1: len(y_train) / (2 * n_pos)}

    # Callbacks
    early_stop = keras.callbacks.EarlyStopping(
        monitor='val_loss', patience=10, restore_best_weights=True
    )
    reduce_lr = keras.callbacks.ReduceLROnPlateau(
        monitor='val_loss', factor=0.5, patience=5, min_lr=1e-6
    )

    history = model.fit(
        X_train, y_train,
        validation_data=(X_val, y_val),
        epochs=epochs,
        batch_size=batch_size,
        class_weight=class_weight,
        callbacks=[early_stop, reduce_lr],
        verbose=0
    )

    # Metriques
    from sklearn.metrics import f1_score, accuracy_score, precision_score, recall_score

    y_pred = (model.predict(X_val, verbose=0) >= 0.5).astype(int).flatten()
    f1 = f1_score(y_val, y_pred)
    acc = accuracy_score(y_val, y_pred)
    prec = precision_score(y_val, y_pred)
    rec = recall_score(y_val, y_pred)
    best_epoch = len(history.history['loss']) - early_stop.patience if early_stop.stopped_epoch > 0 else len(history.history['loss'])

    return model, f1, acc, prec, rec, best_epoch


def main():
    parser = argparse.ArgumentParser(description="Train CNN sur spectrogrammes (datarmor)")
    parser.add_argument("--bruyants", type=str,
                        default=os.path.join(DATARMOR_WORK, "segments_bruyants_v2"),
                        help="Dossier segments bruyants")
    parser.add_argument("--normaux", type=str,
                        default=os.path.join(DATARMOR_WORK, "segments_normaux"),
                        help="Dossier segments normaux")
    parser.add_argument("--max-per-class", type=int, default=None,
                        help="Limiter le nombre par classe (pour test rapide)")
    parser.add_argument("--epochs", type=int, default=60,
                        help="Nombre max d'epochs (defaut: 60)")
    parser.add_argument("--batch-size", type=int, default=128,
                        help="Batch size (defaut: 128, V100 32GB)")
    parser.add_argument("--workers", type=int, default=48,
                        help="Workers pour chargement (defaut: 48)")
    parser.add_argument("--output", type=str,
                        default=os.path.join(DATARMOR_WORK, "cnn_model"),
                        help="Dossier de sortie du modele")
    args = parser.parse_args()

    print("=" * 70)
    print("  CNN TRAINING SUR MEL-SPECTROGRAMMES")
    print(f"  CPU: {os.cpu_count()} cores | Epochs: {args.epochs} | Batch: {args.batch_size}")
    print("=" * 70)

    # Verifier les dossiers
    if not Path(args.bruyants).exists():
        print(f"ERREUR: {args.bruyants} non trouve")
        return 1
    if not Path(args.normaux).exists():
        print(f"ERREUR: {args.normaux} non trouve")
        return 1

    # Charger les spectrogrammes
    print(f"\n[1/4] Chargement des spectrogrammes...")
    X, y, X_mean, X_std = load_all_spectrograms(
        args.bruyants, args.normaux,
        max_per_class=args.max_per_class,
        workers=args.workers
    )

    print(f"\n  Dataset: {X.shape[0]} samples")
    print(f"  Shape: {X.shape}")
    print(f"  Labels: {(y==1).sum()} bruyant, {(y==0).sum()} normal")
    print(f"  Normalisation: mean={X_mean:.4f}, std={X_std:.4f}")

    # 5-Fold CV
    print(f"\n[2/4] 5-Fold Cross-Validation...")
    from sklearn.model_selection import StratifiedKFold

    kfold = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    fold_results = []
    best_f1 = 0
    best_model = None

    for fold, (train_idx, val_idx) in enumerate(kfold.split(X, y), 1):
        print(f"\n  --- Fold {fold}/5 ---")
        X_train, X_val = X[train_idx], X[val_idx]
        y_train, y_val = y[train_idx], y[val_idx]

        print(f"  Train: {len(X_train)} | Val: {len(X_val)}")

        model, f1, acc, prec, rec, best_epoch = train_fold(
            X_train, y_train, X_val, y_val,
            X.shape[1:], args.epochs, args.batch_size, fold
        )

        fold_results.append({"fold": fold, "f1": f1, "acc": acc, "prec": prec, "rec": rec, "epoch": best_epoch})
        print(f"  F1={f1:.4f}  Acc={acc:.4f}  Prec={prec:.4f}  Rec={rec:.4f}  (epoch {best_epoch})")

        if f1 > best_f1:
            best_f1 = f1
            best_model = model

        # Liberer memoire
        import tensorflow as tf
        if fold < 5:
            del model
            tf.keras.backend.clear_session()

    # Resultats
    print(f"\n[3/4] Resultats")
    print(f"\n{'=' * 70}")
    print(f"{'Fold':<8} {'F1':<10} {'Accuracy':<12} {'Precision':<12} {'Recall':<10} {'Epoch':<8}")
    print(f"{'-' * 60}")

    for r in fold_results:
        print(f"{r['fold']:<8} {r['f1']:<10.4f} {r['acc']:<12.4f} {r['prec']:<12.4f} {r['rec']:<10.4f} {r['epoch']:<8}")

    mean_f1 = np.mean([r['f1'] for r in fold_results])
    std_f1 = np.std([r['f1'] for r in fold_results])
    mean_acc = np.mean([r['acc'] for r in fold_results])
    std_acc = np.std([r['acc'] for r in fold_results])

    print(f"\nMoyenne: F1={mean_f1:.4f} (+/- {std_f1:.4f})  Acc={mean_acc:.4f} (+/- {std_acc:.4f})")
    print(f"{'=' * 70}")

    # Re-entrainer sur tout le dataset avec le meilleur modele
    print(f"\n[4/4] Entrainement final sur tout le dataset...")

    import tensorflow as tf
    tf.keras.backend.clear_session()
    tf.random.set_seed(42)

    final_model = build_cnn(X.shape[1:])

    n_pos = (y == 1).sum()
    n_neg = (y == 0).sum()
    class_weight = {0: len(y) / (2 * n_neg), 1: len(y) / (2 * n_pos)}

    # Split 90/10 pour early stopping
    from sklearn.model_selection import train_test_split
    X_train_f, X_val_f, y_train_f, y_val_f = train_test_split(
        X, y, test_size=0.1, stratify=y, random_state=42
    )

    early_stop = tf.keras.callbacks.EarlyStopping(
        monitor='val_loss', patience=10, restore_best_weights=True
    )
    reduce_lr = tf.keras.callbacks.ReduceLROnPlateau(
        monitor='val_loss', factor=0.5, patience=5, min_lr=1e-6
    )

    history = final_model.fit(
        X_train_f, y_train_f,
        validation_data=(X_val_f, y_val_f),
        epochs=args.epochs,
        batch_size=args.batch_size,
        class_weight=class_weight,
        callbacks=[early_stop, reduce_lr],
        verbose=1
    )

    # Sauvegarder
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Modele complet .h5 (compatible TF 2.8 / 2.15)
    model_path = output_dir / "cnn_noisy_car.h5"
    final_model.save(str(model_path))
    print(f"\nModele: {model_path} ({model_path.stat().st_size / 1024 / 1024:.1f} MB)")

    # Sauvegarder config de normalisation
    config = {
        "sr": SR,
        "duration": DURATION,
        "n_mels": N_MELS,
        "hop_length": HOP_LENGTH,
        "n_fft": N_FFT,
        "X_mean": X_mean,
        "X_std": X_std,
        "input_shape": list(X.shape[1:]),
        "n_samples": int(X.shape[0]),
        "n_bruyant": int((y == 1).sum()),
        "n_normal": int((y == 0).sum()),
        "cv_f1_mean": float(mean_f1),
        "cv_f1_std": float(std_f1),
        "cv_acc_mean": float(mean_acc),
        "cv_acc_std": float(std_acc),
    }

    config_path = output_dir / "cnn_config.json"
    with open(config_path, "w") as f:
        json.dump(config, f, indent=2)
    print(f"Config: {config_path}")

    # Resume
    print(f"\n{'=' * 70}")
    print(f"  RESUME")
    print(f"{'=' * 70}")
    print(f"  Dataset: {X.shape[0]} samples ({(y==1).sum()} bruyant, {(y==0).sum()} normal)")
    print(f"  Input: mel-spectrogramme {N_MELS}x{X.shape[2]}")
    print(f"  5-Fold CV: F1={mean_f1:.4f} (+/- {std_f1:.4f})")
    print(f"  Modele: {model_path}")
    print(f"\n  Comparaison:")
    print(f"    RF/GB (225 features):  F1=0.962")
    print(f"    CNN (spectrogrammes):  F1={mean_f1:.4f}")
    print(f"\nTermine.")


if __name__ == "__main__":
    main()
