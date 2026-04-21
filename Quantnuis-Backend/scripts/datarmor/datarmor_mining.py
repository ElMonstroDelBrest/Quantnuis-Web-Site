#!/usr/bin/env python3
"""
=============================================================================
  DATARMOR MINING - Scanner les enregistrements longs pour voitures bruyantes
=============================================================================

Version FAST + PARALLELE (56 coeurs datarmor)

Chemins datarmor:
    Audio:   /home/datawork-osmose/dataset/QUANTNUIS/
    Travail: /home4/datahome/gdgheras/

Usage:
    # Test sur 1 fichier (56 coeurs)
    python datarmor_mining.py --max-files 1 --skip-silence

    # Scan complet + export segments
    python datarmor_mining.py --skip-silence --export-segments segments_bruyants/

    # Moins de workers si besoin
    python datarmor_mining.py --skip-silence --workers 28
=============================================================================
"""

import os
os.environ["JOBLIB_START_METHOD"] = "forkserver"
os.environ["OMP_NUM_THREADS"] = "1"
import sys
import pickle
import argparse
import warnings
warnings.filterwarnings("ignore")

import numpy as np
import pandas as pd
import soundfile as sf
from pathlib import Path
from datetime import timedelta
from concurrent.futures import ProcessPoolExecutor, as_completed

try:
    import librosa
except ImportError:
    print("ERREUR: pip install librosa")
    sys.exit(1)

SR = 22050

# Chemins datarmor
DATARMOR_AUDIO = "/home/datawork-osmose/dataset/QUANTNUIS/"
DATARMOR_WORK = "/home4/datahome/gdgheras/"


# =============================================================================
#  WORKER (chaque process traite un batch de fenetres)
# =============================================================================

def extract_fast(y, sr):
    """Extrait les 15 features du RF V2 (1192 samples)."""
    from scipy.signal import find_peaks

    f = {}

    # MFCCs (indices 12, 22, 24, 26, 28, 30, 32, 34)
    mfccs = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=40)
    f['mfcc_12_mean'] = float(np.mean(mfccs[11]))
    f['mfcc_22_mean'] = float(np.mean(mfccs[21]))
    f['mfcc_24_mean'] = float(np.mean(mfccs[23]))
    f['mfcc_26_mean'] = float(np.mean(mfccs[25]))
    f['mfcc_28_mean'] = float(np.mean(mfccs[27]))
    f['mfcc_30_mean'] = float(np.mean(mfccs[29]))
    f['mfcc_32_mean'] = float(np.mean(mfccs[31]))
    f['mfcc_34_mean'] = float(np.mean(mfccs[33]))

    # Delta MFCCs
    mfccs13 = mfccs[:13]
    delta = librosa.feature.delta(mfccs13)
    f['delta_mfcc_1_std'] = float(np.std(delta[0]))
    f['delta_mfcc_3_std'] = float(np.std(delta[2]))
    f['delta_mfcc_12_std'] = float(np.std(delta[11]))

    # Spectral contrast
    scon = librosa.feature.spectral_contrast(y=y, sr=sr)
    f['spectral_contrast_std'] = float(np.std(scon))

    # Dominant peak frequency
    S = np.abs(librosa.stft(y))
    freqs = librosa.fft_frequencies(sr=sr)
    S_mean = np.mean(S, axis=1)
    pk, props = find_peaks(S_mean, height=np.mean(S_mean), prominence=np.std(S_mean))
    if len(pk) > 0 and 'peak_heights' in props:
        f['dominant_peak_freq'] = float(freqs[pk[np.argmax(props['peak_heights'])]])
    else:
        f['dominant_peak_freq'] = 0.0

    # dB peaks count
    rms = librosa.feature.rms(y=y)[0]
    rms_db = librosa.amplitude_to_db(rms + 1e-10)
    thr = np.mean(rms_db) + np.std(rms_db)
    f['db_peaks_count'] = float(np.sum(rms_db > thr))

    # Onset
    onset = librosa.onset.onset_strength(y=y, sr=sr)
    f['onset_std'] = float(np.std(onset))

    return f


def process_batch(args):
    """Traite un batch de fenetres sequentiellement. 1 batch = 1 process."""
    import warnings
    warnings.filterwarnings("ignore")
    os.environ["OMP_NUM_THREADS"] = "1"

    filepath, offsets, window_sec, feature_names, scaler_params, rf_pkl, \
        skip_silence, silence_db = args

    import pickle as _pkl
    rf = _pkl.loads(rf_pkl)
    rf.n_jobs = 1  # 1 coeur par worker, pas tous
    # Reconstruire le scaler
    from sklearn.preprocessing import StandardScaler
    scaler = StandardScaler()
    scaler.mean_ = scaler_params["mean"]
    scaler.scale_ = scaler_params["scale"]
    scaler.var_ = scaler_params["var"]
    scaler.n_features_in_ = len(feature_names)

    results = []
    fname = Path(filepath).name

    for offset in offsets:
        try:
            y, _ = librosa.load(filepath, sr=SR, offset=offset, duration=window_sec)
        except Exception:
            continue

        if len(y) < SR * 0.5:
            continue

        # Skip silence
        if skip_silence:
            rms_val = np.sqrt(np.mean(y**2))
            db_val = 20 * np.log10(rms_val + 1e-10)
            if db_val < silence_db:
                continue

        y = librosa.util.normalize(y)
        try:
            feats_dict = extract_fast(y, SR)
        except Exception:
            continue

        feats = np.array([feats_dict.get(f, 0.0) for f in feature_names])
        feats = np.nan_to_num(feats, nan=0.0, posinf=0.0, neginf=0.0)
        feats_scaled = scaler.transform(feats.reshape(1, -1))
        proba = float(rf.predict_proba(feats_scaled)[0, 1])

        results.append({
            "file": fname,
            "offset_sec": round(offset, 1),
            "end_sec": round(offset + window_sec, 1),
            "timestamp": str(timedelta(seconds=int(offset))),
            "proba": round(proba, 4),
        })

    return results


# =============================================================================
#  FONCTIONS UTILITAIRES
# =============================================================================

def get_file_duration(filepath):
    try:
        info = sf.info(str(filepath))
        return info.duration
    except Exception:
        try:
            return librosa.get_duration(path=str(filepath))
        except Exception:
            return 0


def format_timestamp(seconds):
    return str(timedelta(seconds=int(seconds)))


# =============================================================================
#  SCANNER PARALLELE
# =============================================================================

def scan_file(filepath, model_data, window_sec, overlap, threshold,
              skip_silence, silence_db, workers):
    """Scanne un WAV long en parallele."""

    duration = get_file_duration(filepath)
    if duration == 0:
        print(f"  ERREUR: impossible de lire {filepath}", flush=True)
        return []

    fname = Path(filepath).name
    hop_sec = window_sec * (1 - overlap)
    n_windows = int((duration - window_sec) / hop_sec) + 1

    print(f"\n  {fname}: {duration/3600:.1f}h ({duration:.0f}s), "
          f"{n_windows} fenetres, {workers} workers", flush=True)

    # Preparer les offsets
    all_offsets = [i * hop_sec for i in range(n_windows)]

    # Decouper en batches (1 batch par worker, equilibre)
    batch_size = max(1, len(all_offsets) // workers)
    batches = []
    for start in range(0, len(all_offsets), batch_size):
        batches.append(all_offsets[start:start + batch_size])

    # Serialiser RF et scaler pour les workers
    rf_pkl = pickle.dumps(model_data["rf"])
    scaler_params = {
        "mean": model_data["scaler"].mean_,
        "scale": model_data["scaler"].scale_,
        "var": model_data["scaler"].var_,
    }
    feature_names = model_data["feature_names"]

    # Lancer les workers
    tasks = [
        (str(filepath), batch, window_sec, feature_names, scaler_params,
         rf_pkl, skip_silence, silence_db)
        for batch in batches
    ]

    all_results = []
    done_batches = 0

    with ProcessPoolExecutor(max_workers=workers) as executor:
        futures = {executor.submit(process_batch, t): i for i, t in enumerate(tasks)}

        for future in as_completed(futures):
            batch_results = future.result()
            all_results.extend(batch_results)
            done_batches += 1

            n_noisy = sum(1 for r in all_results if r["proba"] >= threshold)
            pct = done_batches / len(batches) * 100
            print(f"    [{pct:5.1f}%] {done_batches}/{len(batches)} batches, "
                  f"{len(all_results)} analyses, {n_noisy} bruyants",
                  flush=True)

    return all_results


def export_segments(filepath, results, threshold, output_dir, window_sec):
    """Exporte les segments bruyants en WAV."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    noisy = [r for r in results if r["proba"] >= threshold]
    fname = Path(filepath).stem
    exported = 0

    for r in noisy:
        try:
            y, _ = librosa.load(filepath, sr=SR, offset=r["offset_sec"],
                                duration=window_sec)
        except Exception:
            continue

        ts = r["timestamp"].replace(":", "")
        out_name = f"{fname}_t{ts}_p{r['proba']:.2f}.wav"
        sf.write(str(output_dir / out_name), y, SR)
        exported += 1

    return exported


def export_normal(filepath, results, output_dir, window_sec, max_per_file=200):
    """Exporte des segments normaux (non-silence, proba basse = voiture normale).

    Selectionne les segments avec 0.1 <= proba < 0.3 (activite audio mais pas bruyant).
    Echantillonne aleatoirement pour ne pas en exporter trop.
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Segments avec activite mais pas bruyants (voitures normales probables)
    normal = [r for r in results if 0.1 <= r["proba"] < 0.3]
    fname = Path(filepath).stem

    # Echantillonner si trop nombreux
    rng = np.random.RandomState(42)
    if len(normal) > max_per_file:
        indices = rng.choice(len(normal), size=max_per_file, replace=False)
        normal = [normal[i] for i in sorted(indices)]

    exported = 0
    for r in normal:
        try:
            y, _ = librosa.load(filepath, sr=SR, offset=r["offset_sec"],
                                duration=window_sec)
        except Exception:
            continue

        ts = r["timestamp"].replace(":", "")
        out_name = f"{fname}_t{ts}_p{r['proba']:.2f}.wav"
        sf.write(str(output_dir / out_name), y, SR)
        exported += 1

    return exported


# =============================================================================
#  MAIN
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Datarmor Mining - Vehicules bruyants (FAST + PARALLELE)")
    parser.add_argument("--source", type=str, default=DATARMOR_AUDIO,
                        help=f"Dossier ou fichier WAV (defaut: {DATARMOR_AUDIO})")
    parser.add_argument("--model", type=str,
                        default=os.path.join(DATARMOR_WORK, "rf_mining_model.pkl"),
                        help="Chemin vers le modele RF")
    parser.add_argument("--threshold", type=float, default=0.6,
                        help="Seuil de confiance (defaut: 0.6)")
    parser.add_argument("--window", type=float, default=4.0,
                        help="Taille fenetre en secondes (defaut: 4.0)")
    parser.add_argument("--overlap", type=float, default=0.5,
                        help="Overlap entre fenetres 0-1 (defaut: 0.5)")
    parser.add_argument("--skip-silence", action="store_true",
                        help="Ignorer les fenetres silencieuses")
    parser.add_argument("--silence-db", type=float, default=-50,
                        help="Seuil silence en dB (defaut: -50)")
    parser.add_argument("--export-segments", type=str, default=None,
                        help="Dossier pour exporter les segments bruyants en WAV")
    parser.add_argument("--export-normal", type=str, default=None,
                        help="Dossier pour exporter des segments normaux (voitures non-bruyantes)")
    parser.add_argument("--normal-per-file", type=int, default=200,
                        help="Max segments normaux par fichier audio (defaut: 200)")
    parser.add_argument("--max-files", type=int, default=None,
                        help="Limiter le nombre de fichiers")
    parser.add_argument("--workers", type=int, default=48,
                        help="Nombre de workers paralleles (defaut: 48)")
    parser.add_argument("--output", type=str,
                        default=os.path.join(DATARMOR_WORK, "mining_results.csv"),
                        help="Fichier CSV de sortie")
    args = parser.parse_args()

    print("=" * 70)
    print("  DATARMOR MINING - Detection de vehicules bruyants")
    print(f"  FAST + PARALLELE ({args.workers} workers)")
    print("=" * 70)

    # Charger modele
    model_path = Path(args.model)
    if not model_path.exists():
        print(f"ERREUR: modele non trouve: {model_path}")
        return 1

    with open(model_path, "rb") as f:
        model_data = pickle.load(f)

    print(f"Modele: {model_path.name}")
    print(f"  Features: {model_data['n_features']} ({', '.join(model_data['feature_names'][:5])}...)")
    print(f"  F1 CV: {model_data['f1_cv']:.4f}")

    # Trouver fichiers
    source = Path(args.source)
    if source.is_file():
        audio_files = [source]
    else:
        audio_files = sorted(
            list(source.glob("*.WAV")) +
            list(source.glob("*.wav"))
        )

    if args.max_files:
        audio_files = audio_files[:args.max_files]

    total_duration = 0
    for af in audio_files:
        total_duration += get_file_duration(af)

    print(f"\nFichiers: {len(audio_files)}")
    print(f"Duree totale: {total_duration/3600:.1f} heures")
    print(f"Seuil: {args.threshold}, Fenetre: {args.window}s, Overlap: {args.overlap}")
    if args.skip_silence:
        print(f"Skip silence: < {args.silence_db} dB")
    print("=" * 70)

    # Scanner
    all_results = []
    for i, filepath in enumerate(audio_files):
        print(f"\n[{i+1}/{len(audio_files)}] Scanning...", flush=True)
        results = scan_file(
            filepath, model_data, args.window, args.overlap,
            args.threshold, args.skip_silence, args.silence_db, args.workers
        )
        all_results.extend(results)

        # Export au fur et a mesure
        if args.export_segments and results:
            n_exp = export_segments(
                filepath, results, args.threshold,
                args.export_segments, args.window
            )
            print(f"  Exporte: {n_exp} segments bruyants", flush=True)

        if args.export_normal and results:
            n_norm = export_normal(
                filepath, results, args.export_normal,
                args.window, args.normal_per_file
            )
            print(f"  Exporte: {n_norm} segments normaux", flush=True)

    # Resultats
    all_results.sort(key=lambda x: x.get("proba", 0), reverse=True)

    n_noisy = sum(1 for r in all_results if r.get("proba", 0) >= args.threshold)
    n_uncertain = sum(1 for r in all_results if 0.4 <= r.get("proba", 0) < args.threshold)
    n_normal = sum(1 for r in all_results if r.get("proba", 0) < 0.4)

    print(f"\n{'=' * 70}")
    print(f"  RESULTATS")
    print(f"{'=' * 70}")
    print(f"  Fenetres analysees: {len(all_results)}")
    print(f"  BRUYANT  (>= {args.threshold}): {n_noisy}")
    print(f"  INCERTAIN (0.4-{args.threshold}): {n_uncertain}")
    print(f"  NORMAL   (< 0.4): {n_normal}")

    if n_noisy > 0:
        print(f"\n  Top 30 segments bruyants:")
        for r in all_results[:30]:
            if r.get("proba", 0) >= args.threshold:
                print(f"    {r['proba']:.3f}  {r['file']}  "
                      f"{r['timestamp']}-{format_timestamp(r['end_sec'])}")

    # Sauvegarder CSV
    if all_results:
        df = pd.DataFrame(all_results)
        df.to_csv(args.output, index=False)
        print(f"\nResultats: {args.output}")

        print(f"\nStats par fichier:")
        for fname in df["file"].unique():
            sub = df[df["file"] == fname]
            n = (sub["proba"] >= args.threshold).sum()
            print(f"  {fname}: {n} bruyants / {len(sub)} total")

    if args.export_segments:
        total_exp = len(list(Path(args.export_segments).glob("*.wav")))
        print(f"\nSegments exportes: {total_exp} dans {args.export_segments}/")

    print("\nTermine.")


if __name__ == "__main__":
    main()
