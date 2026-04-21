#!/usr/bin/env python3
"""
Entraînement du CRNN CarDetector sur mel-spectrogrammes.

Usage:
    cd Quantnuis-Backend
    python -m models.car_detector.train_crnn
    python -m models.car_detector.train_crnn --duration 4.0 --n-mels 128
"""

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import tensorflow as tf
from tensorflow.keras import layers, models, regularizers
from sklearn.model_selection import StratifiedKFold
from sklearn.metrics import f1_score, classification_report
import pandas as pd

from config import get_settings
from shared import print_header, print_success, print_info, print_warning, print_error
from shared.audio_utils import load_melspectrogram
from . import config

settings = get_settings()


# ==============================================================================
# CONFIGURATION
# ==============================================================================

def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument('--sr', type=int, default=22050)
    p.add_argument('--duration', type=float, default=4.0)
    p.add_argument('--n-mels', type=int, default=128)
    p.add_argument('--n-fft', type=int, default=2048)
    p.add_argument('--hop-length', type=int, default=512)
    p.add_argument('--epochs', type=int, default=50)
    p.add_argument('--batch-size', type=int, default=16)
    p.add_argument('--cv-folds', type=int, default=5)
    p.add_argument('--min-reliability', type=int, default=1,
                   help='Fiabilité minimale des annotations (1-3, défaut=1 pour utiliser tout le dataset)')
    p.add_argument('--balance', action='store_true', default=True,
                   help='Équilibrer les classes par sous-échantillonnage')
    p.add_argument('--no-balance', dest='balance', action='store_false')
    return p.parse_args()


# ==============================================================================
# CHARGEMENT AUDIO → MEL-SPECTROGRAMME
# ==============================================================================

def load_spectrogram(path: Path, sr: int, duration: float,
                     n_mels: int, n_fft: int, hop_length: int):
    """Charge un fichier audio et retourne son mel-spectrogramme en dB."""
    mel_db = load_melspectrogram(str(path), sr, duration, n_mels, n_fft, hop_length)
    if mel_db is None:
        print_warning(f"Erreur sur {path.name}")
    return mel_db


# ==============================================================================
# ARCHITECTURE CRNN
# ==============================================================================

def build_crnn(input_shape: tuple) -> tf.keras.Model:
    """
    CRNN : CNN 2D → reshape temporal → GRU → Dense.

    input_shape: (n_mels, time_frames, 1)
    """
    inp = layers.Input(shape=input_shape)

    # Bloc CNN 1
    x = layers.Conv2D(16, (3, 3), padding='same', activation='relu')(inp)
    x = layers.BatchNormalization()(x)
    x = layers.MaxPooling2D((2, 2))(x)
    x = layers.Dropout(0.2)(x)

    # Bloc CNN 2
    x = layers.Conv2D(32, (3, 3), padding='same', activation='relu')(x)
    x = layers.BatchNormalization()(x)
    x = layers.MaxPooling2D((2, 2))(x)
    x = layers.Dropout(0.2)(x)

    # Bloc CNN 3
    x = layers.Conv2D(64, (3, 3), padding='same', activation='relu')(x)
    x = layers.BatchNormalization()(x)
    x = layers.MaxPooling2D((2, 2))(x)
    x = layers.Dropout(0.2)(x)

    # Reshape pour la RNN : (batch, freq', time', 64) → (batch, time', freq'*64)
    x = layers.Permute((2, 1, 3))(x)
    time_prime = x.shape[1]
    freq_prime = x.shape[2]
    ch = x.shape[3]
    x = layers.Reshape((time_prime, freq_prime * ch))(x)

    # GRU — 128 unités pour absorber les 1024 features (16 mel × 64 canaux)
    x = layers.GRU(128, return_sequences=False)(x)
    x = layers.Dropout(0.3)(x)

    # Classificateur
    x = layers.Dense(64, activation='relu',
                     kernel_regularizer=regularizers.l2(0.001))(x)
    x = layers.Dropout(0.2)(x)
    out = layers.Dense(1, activation='sigmoid')(x)

    model = models.Model(inputs=inp, outputs=out)
    model.compile(
        optimizer=tf.keras.optimizers.Adam(learning_rate=5e-4),
        loss='binary_crossentropy',
        metrics=['accuracy']
    )
    return model


# ==============================================================================
# AUGMENTATION
# ==============================================================================

def augment(X: np.ndarray, y: np.ndarray, factor: int = 2) -> tuple:
    """Augmente le dataset : shift temporel + bruit gaussien + freq/time masking."""
    X_aug, y_aug = [X], [y]
    n, n_mels, n_frames, _ = X.shape

    for i in range(factor - 1):
        X_new = X.copy()

        # Shift temporel
        shift = np.random.randint(1, n_frames // 4)
        X_new = np.roll(X_new, shift, axis=2)

        # Bruit gaussien (SNR ~20dB)
        if i % 3 == 0:
            noise = np.random.normal(0, 0.05, X_new.shape).astype(np.float32)
            X_new = X_new + noise

        # Frequency masking (SpecAugment)
        if i % 3 == 1:
            f0 = np.random.randint(0, n_mels // 4)
            f = np.random.randint(1, n_mels // 8)
            X_new[:, f0:f0 + f, :, :] = X_new.min()

        # Time masking (SpecAugment)
        if i % 3 == 2:
            t0 = np.random.randint(0, n_frames // 4)
            t = np.random.randint(1, n_frames // 8)
            X_new[:, :, t0:t0 + t, :] = X_new.min()

        X_aug.append(X_new)
        y_aug.append(y)

    return np.concatenate(X_aug), np.concatenate(y_aug)


# ==============================================================================
# MAIN
# ==============================================================================

def main():
    args = parse_args()

    # GPU
    gpus = tf.config.list_physical_devices('GPU')
    device = f"GPU ({len(gpus)})" if gpus else "CPU"
    for gpu in gpus:
        tf.config.experimental.set_memory_growth(gpu, True)
    print_info(f"Device: {device}")

    # 1. Charger les annotations
    print_header("Chargement du dataset")
    df = pd.read_csv(config.ANNOTATION_CSV)
    df = df[df['reliability'] >= args.min_reliability]
    print_info(f"{len(df)} annotations (fiabilité >= {args.min_reliability})")
    print_info(f"  Voiture (1): {(df['label']==1).sum()}")
    print_info(f"  Pas voiture (0): {(df['label']==0).sum()}")

    # Équilibrage par sous-échantillonnage de la classe majoritaire
    if args.balance:
        n_min = min((df['label'] == 0).sum(), (df['label'] == 1).sum())
        df = pd.concat([
            df[df['label'] == 0].sample(n=n_min, random_state=42),
            df[df['label'] == 1].sample(n=n_min, random_state=42),
        ]).reset_index(drop=True)
        print_info(f"Après équilibrage: {len(df)} samples ({n_min} par classe)")

    slices_dir = config.SLICES_DIR

    # 2. Charger en numpy memmap (une seule lecture, accès O(1))
    MMAP_X = Path('/tmp/car_spectros.dat')
    MMAP_Y = Path('/tmp/car_labels.npy')

    paths, y_list = [], []
    skipped = 0
    for _, row in df.iterrows():
        path = slices_dir / row['nfile']
        if path.exists():
            paths.append(path)
            y_list.append(int(row['label']))
        else:
            skipped += 1
    if skipped:
        print_warning(f"{skipped} fichiers ignorés")
    if not paths:
        print_error("Aucun fichier trouvé."); sys.exit(1)

    n = len(paths)

    # Shape test
    test_s = load_spectrogram(paths[0], args.sr, args.duration,
                              args.n_mels, args.n_fft, args.hop_length)
    n_mels, n_frames = test_s.shape
    input_shape = (n_mels, n_frames, 1)

    if not MMAP_X.exists() or MMAP_Y.exists() and np.load(MMAP_Y).shape[0] != n:
        print_header(f"Pré-calcul spectros → {MMAP_X} ({n} samples)")
        mm = np.memmap(MMAP_X, dtype='float32', mode='w+', shape=(n, n_mels, n_frames))
        for i, p in enumerate(paths):
            if i % 2000 == 0: print_info(f"  {i}/{n}...")
            s = load_spectrogram(p, args.sr, args.duration,
                                 args.n_mels, args.n_fft, args.hop_length)
            mm[i] = s if s is not None else 0.0
        mm.flush()
        np.save(MMAP_Y, np.array(y_list))
        print_success("Pré-calcul terminé")
    else:
        print_info(f"Memmap existant chargé ({n} samples)")

    mm = np.memmap(MMAP_X, dtype='float32', mode='r', shape=(n, n_mels, n_frames))
    y = np.load(MMAP_Y)

    print_success(f"Dataset: {n} samples, shape spectro=({n_mels}, {n_frames})")

    # 3. Normalisation — stats exhaustives sur le dataset complet (streaming par chunks)
    print_info("Calcul des stats de normalisation (dataset complet)...")
    _chunk = 512
    _sum, _sq, _count = 0.0, 0.0, 0
    for _s in range(0, n, _chunk):
        _c = mm[_s:min(_s + _chunk, n)].astype(np.float64)
        _sum   += _c.sum()
        _sq    += (_c * _c).sum()
        _count += _c.size
    X_mean = float(_sum / _count)
    X_std  = float(np.sqrt(max(_sq / _count - X_mean ** 2, 0.0)))
    print_info(f"Input shape CRNN: {input_shape}, mean={X_mean:.2f}, std={X_std:.2f}")

    # Toujours charger en RAM — accès random au memmap = catastrophique avec shuffle
    # (n × 4ms/seek × 50 epochs × 5 folds ≈ 8h). Le dataset fait au max ~3 GB,
    # négligeable sur une machine avec ≥ 16 GB RAM.
    ram_mb = n * n_mels * n_frames * 4 / 1e6
    print_info(f"Chargement en RAM ({ram_mb:.0f} MB)...")
    X_all = ((mm[:] - X_mean) / (X_std + 1e-8)).astype(np.float32)[..., np.newaxis]
    print_success("Dataset en RAM")

    def make_ds(indices, shuffle=False):
        Xi = X_all[indices]
        yi = y[indices].astype(np.float32)
        if shuffle:
            perm = np.random.permutation(len(indices))
            Xi, yi = Xi[perm], yi[perm]
        # Forcer CPU : from_tensor_slices sur large array essaie sinon
        # d'allouer le tensor de 2.5 GB en VRAM → InternalError après 5 folds
        with tf.device('/CPU:0'):
            ds = tf.data.Dataset.from_tensor_slices((Xi, yi))
        return ds.batch(args.batch_size).prefetch(tf.data.AUTOTUNE)

    # 4. Cross-validation stratifiée
    print_header(f"Cross-validation ({args.cv_folds} folds)")
    cv = StratifiedKFold(n_splits=args.cv_folds, shuffle=True, random_state=42)
    f1_scores = []

    for fold, (train_idx, val_idx) in enumerate(cv.split(np.arange(n), y)):
        print_info(f"Fold {fold + 1}/{args.cv_folds}")

        ds_tr = make_ds(train_idx, shuffle=True)
        ds_val = make_ds(val_idx)

        model = build_crnn(input_shape)
        callbacks = [
            tf.keras.callbacks.EarlyStopping(patience=8, restore_best_weights=True, monitor='val_loss'),
            tf.keras.callbacks.ReduceLROnPlateau(patience=4, factor=0.5, min_lr=1e-5)
        ]
        model.fit(ds_tr, validation_data=ds_val, epochs=args.epochs, callbacks=callbacks, verbose=0)

        y_pred, y_true = [], []
        for xb, yb in ds_val:
            y_pred.extend((model(xb, training=False).numpy() > 0.5).astype(int).flatten())
            y_true.extend(yb.numpy().astype(int))
        f1 = f1_score(y_true, y_pred)
        f1_scores.append(f1)
        print_info(f"  Fold {fold + 1} F1 = {f1:.4f}")

    cv_f1_mean = float(np.mean(f1_scores))
    cv_f1_std = float(np.std(f1_scores))
    print_success(f"CV F1 = {cv_f1_mean:.4f} ± {cv_f1_std:.4f}")

    # 5. Entraînement final
    # Libérer la VRAM des 5 modèles CV avant de créer le modèle final
    tf.keras.backend.clear_session()
    import gc; gc.collect()

    print_header("Entraînement final (dataset complet)")
    ds_all = make_ds(np.arange(n), shuffle=True)
    final_model = build_crnn(input_shape)
    final_model.fit(ds_all, epochs=args.epochs, callbacks=[
        tf.keras.callbacks.EarlyStopping(patience=10, restore_best_weights=True, monitor='loss')
    ], verbose=1)

    # 6. Rapport final (IN-SAMPLE — pour diagnostic uniquement, non représentatif)
    # La métrique officielle est le CV F1 calculé ci-dessus.
    y_pred_all, y_true_all = [], []
    for xb, yb in make_ds(np.arange(n)):
        y_pred_all.extend((final_model(xb, training=False).numpy() > 0.5).astype(int).flatten())
        y_true_all.extend(yb.numpy().astype(int))
    print_warning("[IN-SAMPLE] Rapport sur le dataset d'entraînement complet (score gonflé, diagnostic uniquement) :")
    print_info(f"  Métrique officielle : CV F1 = {cv_f1_mean:.4f} +/- {cv_f1_std:.4f}")
    print(classification_report(y_true_all, y_pred_all, target_names=['PAS_VOITURE', 'VOITURE']))

    # 7. Sauvegarde
    print_header("Sauvegarde des artifacts")
    config.ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)

    final_model.save(str(config.CRNN_MODEL_PATH))
    print_success(f"Modèle sauvegardé : {config.CRNN_MODEL_PATH}")

    crnn_cfg = {
        'sr': args.sr,
        'duration': args.duration,
        'n_mels': args.n_mels,
        'n_fft': args.n_fft,
        'hop_length': args.hop_length,
        'X_mean': X_mean,
        'X_std': X_std,
        'input_shape': list(input_shape),
        'n_samples': len(y),
        'cv_f1_mean': cv_f1_mean,
        'cv_f1_std': cv_f1_std,
        'class_distribution': {
            'voiture': int((y == 1).sum()),
            'pas_voiture': int((y == 0).sum()),
        }
    }

    with open(config.CRNN_CONFIG_PATH, 'w') as f:
        json.dump(crnn_cfg, f, indent=2)
    print_success(f"Config sauvegardée : {config.CRNN_CONFIG_PATH}")
    print_success(f"\nCRNN CarDetector entraîné ! CV F1 = {cv_f1_mean:.4f}")


if __name__ == '__main__':
    main()
