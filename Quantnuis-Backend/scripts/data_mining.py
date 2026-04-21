#!/usr/bin/env python3
"""
Data Mining: scanne des fichiers audio avec un RF pré-entraîné
pour trouver les candidats "véhicule bruyant".

Le RF (seed 50/50, F1=0.88) sert de filtre ultra-rapide:
  - proba >= 0.7 → BRUYANT (haute confiance) → ajouter au dataset
  - 0.4 <= proba < 0.7 → INCERTAIN → vérification manuelle
  - proba < 0.4 → NORMAL → ignorer

Usage:
    # Scanner un dossier d'audios
    python -u scripts/data_mining.py /chemin/vers/audios/

    # Scanner avec seuil custom
    python -u scripts/data_mining.py /chemin/vers/audios/ --threshold 0.6

    # Scanner et copier les candidats dans un dossier de review
    python -u scripts/data_mining.py /chemin/vers/audios/ --copy-to review_candidates/

    # Scanner des fichiers longs (découper en fenêtres de 4s)
    python -u scripts/data_mining.py /chemin/vers/audios/ --slice
"""

import argparse
import shutil
import numpy as np
import pandas as pd
import librosa
from pathlib import Path
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import RandomForestClassifier
import warnings
warnings.filterwarnings("ignore")

DATA_DIR = Path("data/noisy_car_detector")
SR = 22050


def load_and_train_rf(n_features=10):
    """Charge les données, crée le seed 50/50, entraîne le RF."""
    df = pd.read_csv(DATA_DIR / "features_all.csv")
    meta = ["nfile", "label", "reliability"]
    feature_cols = [c for c in df.columns if c not in meta]

    X_all = np.nan_to_num(df[feature_cols].values, nan=0.0, posinf=0.0, neginf=0.0)
    y = df["label"].values

    # Feature selection
    rf_sel = RandomForestClassifier(n_estimators=200, random_state=42, n_jobs=-1)
    rf_sel.fit(X_all, y)
    imp = pd.DataFrame({"f": feature_cols, "s": rf_sel.feature_importances_})
    top = imp.sort_values("s", ascending=False).head(n_features)["f"].tolist()

    X = np.nan_to_num(df[top].values, nan=0.0, posinf=0.0, neginf=0.0)

    # Seed 50/50
    rng = np.random.RandomState(42)
    noisy_idx = np.where(y == 1)[0]
    normal_idx = np.where(y == 0)[0]
    normal_sample = rng.choice(normal_idx, size=len(noisy_idx), replace=False)
    seed_idx = np.concatenate([noisy_idx, normal_sample])

    X_seed, y_seed = X[seed_idx], y[seed_idx]

    # Train RF
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X_seed)

    rf = RandomForestClassifier(n_estimators=200, random_state=42, n_jobs=-1, class_weight="balanced")
    rf.fit(X_scaled, y_seed)

    print(f"RF entraîné: seed 50/50 ({len(seed_idx)} samples), {n_features} features")
    print(f"Top features: {', '.join(top[:5])}")

    return rf, scaler, top


def extract_features_from_audio(filepath, feature_names, sr=SR):
    """Extrait les features d'un fichier audio."""
    import sys
    sys.path.insert(0, ".")
    from shared.audio_utils import extract_all_features

    try:
        y, _ = librosa.load(filepath, sr=sr, res_type="soxr_hq")
    except Exception:
        y, _ = librosa.load(filepath, sr=sr)

    if len(y) < sr:  # < 1 seconde
        return None

    all_features = extract_all_features(y, sr)
    return np.array([all_features.get(f, 0.0) for f in feature_names])


def extract_features_from_segment(y, sr, feature_names):
    """Extrait les features d'un segment audio déjà chargé."""
    import sys
    sys.path.insert(0, ".")
    from shared.audio_utils import extract_all_features

    if len(y) < sr:
        return None

    all_features = extract_all_features(y, sr)
    return np.array([all_features.get(f, 0.0) for f in feature_names])


def scan_file(filepath, rf, scaler, feature_names, do_slice=False, slice_dur=4.0):
    """Scanne un fichier audio et retourne les prédictions."""
    results = []

    try:
        y, sr = librosa.load(filepath, sr=SR, res_type="soxr_hq")
    except Exception:
        try:
            y, sr = librosa.load(filepath, sr=SR)
        except Exception as e:
            return [{"file": str(filepath), "segment": "error", "proba": 0, "error": str(e)}]

    duration = len(y) / sr

    if do_slice and duration > slice_dur * 1.5:
        # Découper en fenêtres
        window = int(slice_dur * sr)
        hop = int(slice_dur * sr * 0.5)  # 50% overlap

        for i, start in enumerate(range(0, len(y) - window + 1, hop)):
            segment = y[start:start + window]
            feats = extract_features_from_segment(segment, sr, feature_names)
            if feats is None:
                continue

            feats_clean = np.nan_to_num(feats, nan=0.0, posinf=0.0, neginf=0.0)
            feats_scaled = scaler.transform(feats_clean.reshape(1, -1))
            proba = rf.predict_proba(feats_scaled)[0, 1]

            results.append({
                "file": str(filepath),
                "segment": f"{start/sr:.1f}s-{(start+window)/sr:.1f}s",
                "proba": proba,
                "duration": slice_dur,
            })
    else:
        # Fichier entier
        feats = extract_features_from_audio(filepath, feature_names)
        if feats is None:
            return [{"file": str(filepath), "segment": "too_short", "proba": 0}]

        feats_clean = np.nan_to_num(feats, nan=0.0, posinf=0.0, neginf=0.0)
        feats_scaled = scaler.transform(feats_clean.reshape(1, -1))
        proba = rf.predict_proba(feats_scaled)[0, 1]

        results.append({
            "file": str(filepath),
            "segment": "full",
            "proba": proba,
            "duration": duration,
        })

    return results


def main():
    parser = argparse.ArgumentParser(description="Data Mining - trouver les véhicules bruyants")
    parser.add_argument("source", type=str, help="Dossier ou fichier audio à scanner")
    parser.add_argument("--threshold", type=float, default=0.6, help="Seuil de confiance (défaut: 0.6)")
    parser.add_argument("--copy-to", type=str, default=None, help="Copier les candidats dans ce dossier")
    parser.add_argument("--slice", action="store_true", help="Découper les fichiers longs en fenêtres de 4s")
    parser.add_argument("--features", type=int, default=10, help="Nombre de features")
    args = parser.parse_args()

    print("=" * 60)
    print("  DATA MINING - Détection de véhicules bruyants")
    print("=" * 60)

    # Train RF
    rf, scaler, feature_names = load_and_train_rf(args.features)

    # Find audio files
    source = Path(args.source)
    if source.is_file():
        audio_files = [source]
    else:
        audio_files = sorted(
            list(source.rglob("*.wav")) +
            list(source.rglob("*.mp3")) +
            list(source.rglob("*.flac")) +
            list(source.rglob("*.ogg"))
        )

    print(f"\n{len(audio_files)} fichiers audio trouvés dans {source}")
    print(f"Seuil: {args.threshold}")
    print(f"{'='*60}")

    # Scan
    all_results = []
    for i, filepath in enumerate(audio_files):
        results = scan_file(filepath, rf, scaler, feature_names, do_slice=args.slice)
        all_results.extend(results)

        if (i + 1) % 20 == 0:
            print(f"  Scanné: {i+1}/{len(audio_files)}")

    # Sort by probability (most noisy first)
    all_results.sort(key=lambda x: x.get("proba", 0), reverse=True)

    # Display results
    n_noisy = sum(1 for r in all_results if r.get("proba", 0) >= args.threshold)
    n_uncertain = sum(1 for r in all_results if 0.4 <= r.get("proba", 0) < args.threshold)
    n_normal = sum(1 for r in all_results if r.get("proba", 0) < 0.4)

    print(f"\n{'='*60}")
    print(f"  RESULTATS")
    print(f"{'='*60}")
    print(f"  BRUYANT  (>= {args.threshold}): {n_noisy}")
    print(f"  INCERTAIN (0.4-{args.threshold}): {n_uncertain}")
    print(f"  NORMAL   (< 0.4): {n_normal}")

    if n_noisy > 0:
        print(f"\n  Top candidats bruyants:")
        for r in all_results[:20]:
            if r.get("proba", 0) >= args.threshold:
                fname = Path(r["file"]).name
                seg = r.get("segment", "full")
                print(f"    {r['proba']:.3f}  {fname} [{seg}]")

    # Save results
    results_df = pd.DataFrame(all_results)
    output_path = DATA_DIR / "mining_results.csv"
    results_df.to_csv(output_path, index=False)
    print(f"\nRésultats sauvegardés: {output_path}")

    # Copy candidates
    if args.copy_to and n_noisy > 0:
        copy_dir = Path(args.copy_to)
        copy_dir.mkdir(parents=True, exist_ok=True)
        copied = 0
        for r in all_results:
            if r.get("proba", 0) >= args.threshold and r.get("segment") == "full":
                src = Path(r["file"])
                if src.exists():
                    shutil.copy2(src, copy_dir / src.name)
                    copied += 1
        print(f"Copié {copied} fichiers dans {copy_dir}")


if __name__ == "__main__":
    main()
