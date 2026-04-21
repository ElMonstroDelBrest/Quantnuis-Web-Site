#!/usr/bin/env python3
"""
Extrait les 225 features des segments bruyants candidats.
Parallélisé sur 48 workers pour datarmor (56 coeurs).

Usage:
    python datarmor_extract_features.py
    python datarmor_extract_features.py --input segments_bruyants/ --workers 48
"""

import os
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["NUMBA_DISABLE_JIT"] = "1"

import sys
import warnings
warnings.filterwarnings("ignore")

import numpy as np
import pandas as pd
import argparse
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor, as_completed

DATARMOR_WORK = "/home4/datahome/gdgheras/"
SR = 22050
N_MFCC = 40


def extract_all_features(y, sr):
    """Extrait les 225 features audio."""
    import librosa
    from scipy import signal as scipy_signal
    from scipy.signal import find_peaks

    f = {}

    rms = librosa.feature.rms(y=y)[0]
    f['rms_mean'], f['rms_std'] = np.mean(rms), np.std(rms)

    zcr = librosa.feature.zero_crossing_rate(y)[0]
    f['zcr_mean'], f['zcr_std'] = np.mean(zcr), np.std(zcr)

    sc = librosa.feature.spectral_centroid(y=y, sr=sr)[0]
    f['spectral_centroid_mean'], f['spectral_centroid_std'] = np.mean(sc), np.std(sc)

    sb = librosa.feature.spectral_bandwidth(y=y, sr=sr)[0]
    f['spectral_bandwidth_mean'], f['spectral_bandwidth_std'] = np.mean(sb), np.std(sb)

    sr_f = librosa.feature.spectral_rolloff(y=y, sr=sr)[0]
    f['spectral_rolloff_mean'], f['spectral_rolloff_std'] = np.mean(sr_f), np.std(sr_f)

    sf_feat = librosa.feature.spectral_flatness(y=y)[0]
    f['spectral_flatness_mean'], f['spectral_flatness_std'] = np.mean(sf_feat), np.std(sf_feat)

    scon = librosa.feature.spectral_contrast(y=y, sr=sr)
    f['spectral_contrast_mean'], f['spectral_contrast_std'] = np.mean(scon), np.std(scon)

    harm, perc = librosa.effects.hpss(y)
    f['harm_mean'], f['harm_std'] = np.mean(np.abs(harm)), np.std(harm)
    f['perc_mean'], f['perc_std'] = np.mean(np.abs(perc)), np.std(perc)
    f['harm_perc_ratio'] = np.mean(np.abs(harm)) / (np.mean(np.abs(perc)) + 1e-10)

    mfccs = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=N_MFCC)
    for i in range(N_MFCC):
        f[f'mfcc_{i+1}_mean'], f[f'mfcc_{i+1}_std'] = np.mean(mfccs[i]), np.std(mfccs[i])

    chroma = librosa.feature.chroma_stft(y=y, sr=sr)
    f['chroma_mean'], f['chroma_std'] = np.mean(chroma), np.std(chroma)
    for i in range(12):
        f[f'chroma_{i}_mean'] = np.mean(chroma[i])

    f['energy'] = np.sum(y**2)
    f['max_amplitude'] = np.max(np.abs(y))
    try:
        tempo, _ = librosa.beat.beat_track(y=y, sr=sr)
        f['tempo'] = float(np.asarray(tempo).item() if np.ndim(tempo) > 0 else tempo)
    except Exception:
        f['tempo'] = 0.0

    S = np.abs(librosa.stft(y))
    freqs = librosa.fft_frequencies(sr=sr)

    masks = {'very_low': (freqs >= 20) & (freqs < 100), 'low': (freqs >= 100) & (freqs < 300),
             'mid': (freqs >= 300) & (freqs < 2000), 'high': freqs >= 2000}
    for k, m in masks.items():
        f[f'{k}_freq_energy'] = np.mean(S[m, :]) if m.any() else 0.0

    total = sum(f[f'{k}_freq_energy'] for k in masks) + 1e-10
    f['low_freq_ratio'] = (f['very_low_freq_energy'] + f['low_freq_energy']) / total
    f['low_high_ratio'] = (f['very_low_freq_energy'] + f['low_freq_energy']) / (f['high_freq_energy'] + 1e-10)

    mfccs13 = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=13)
    delta = librosa.feature.delta(mfccs13)
    delta2 = librosa.feature.delta(mfccs13, order=2)
    for i in range(13):
        f[f'delta_mfcc_{i+1}_mean'], f[f'delta_mfcc_{i+1}_std'] = np.mean(delta[i]), np.std(delta[i])
        f[f'delta2_mfcc_{i+1}_mean'] = np.mean(delta2[i])

    mel = librosa.power_to_db(librosa.feature.melspectrogram(y=y, sr=sr, n_mels=128), ref=np.max)
    for name, sl in [('very_low', slice(0, 10)), ('low', slice(10, 30)),
                     ('mid', slice(30, 60)), ('high', slice(60, None))]:
        f[f'mel_{name}_mean'], f[f'mel_{name}_std'] = np.mean(mel[sl, :]), np.std(mel[sl, :])

    mel_diff = np.diff(mel, axis=1)
    f['mel_temporal_var_mean'], f['mel_temporal_var_std'] = np.mean(np.abs(mel_diff)), np.std(np.abs(mel_diff))

    onset = librosa.onset.onset_strength(y=y, sr=sr)
    f['onset_mean'], f['onset_std'] = np.mean(onset), np.std(onset)
    f['onset_max'], f['onset_min'] = np.max(onset), np.min(onset)
    peaks = librosa.util.peak_pick(onset, pre_max=3, post_max=3, pre_avg=3, post_avg=5, delta=0.5, wait=10)
    f['onset_peaks_count'] = len(peaks)
    f['onset_peaks_rate'] = len(peaks) / (len(y) / sr)

    flux = np.sqrt(np.sum(np.diff(S, axis=1)**2, axis=0))
    f['spectral_flux_mean'], f['spectral_flux_std'] = np.mean(flux), np.std(flux)
    f['spectral_flux_max'] = np.max(flux)

    ac = librosa.autocorrelate(y, max_size=sr // 10)
    ac = ac / (ac[0] + 1e-10)
    f['autocorr_peak_value'] = np.max(ac[10:]) if len(ac) > 10 else 0.0
    f['autocorr_mean'] = np.mean(ac[10:]) if len(ac) > 10 else 0.0

    try:
        f0, _, vp = librosa.pyin(y, fmin=50, fmax=500, sr=sr)
        f0v = f0[~np.isnan(f0)]
        if len(f0v) > 0:
            f['f0_mean'], f['f0_std'] = np.mean(f0v), np.std(f0v)
            f['f0_min'], f['f0_max'] = np.min(f0v), np.max(f0v)
            f['f0_range'] = f['f0_max'] - f['f0_min']
            f['estimated_rpm'] = f['f0_mean'] * 60
        else:
            f['f0_mean'] = f['f0_std'] = f['f0_min'] = f['f0_max'] = 0.0
            f['f0_range'] = f['estimated_rpm'] = 0.0
        f['voiced_ratio'] = np.mean(vp[~np.isnan(vp)]) if len(vp[~np.isnan(vp)]) > 0 else 0.0
    except Exception:
        f['f0_mean'] = f['f0_std'] = f['f0_min'] = f['f0_max'] = 0.0
        f['f0_range'] = f['estimated_rpm'] = f['voiced_ratio'] = 0.0

    hp = np.sum(harm**2)
    np_h = np.sum((y - harm)**2)
    f['hnr_db'] = f['hnr_mean'] = 10 * np.log10(hp / (np_h + 1e-10))
    f['hnr_std'] = 0.0

    freqs_psd, psd = scipy_signal.welch(y, sr, nperseg=2048)
    for name, lo, hi in [('motor_low', 50, 150), ('motor_high', 150, 300),
                         ('harmonics', 300, 800), ('exhaust', 800, 2000),
                         ('turbo', 2000, 4000), ('aero', 4000, 8000)]:
        m = (freqs_psd >= lo) & (freqs_psd < hi)
        f[f'psd_{name}'] = np.mean(psd[m]) if m.any() else 0.0
    f['psd_low_high_ratio'] = (f['psd_motor_low'] + f['psd_motor_high']) / (f['psd_turbo'] + f['psd_aero'] + 1e-10)

    S_mean = np.mean(S, axis=1)
    pk, props = find_peaks(S_mean, height=np.mean(S_mean), prominence=np.std(S_mean))
    f['spectral_peaks_count'] = len(pk)
    if len(pk) > 0 and 'peak_heights' in props:
        f['spectral_peaks_mean_height'] = np.mean(props['peak_heights'])
        f['spectral_peaks_max_height'] = np.max(props['peak_heights'])
        f['dominant_peak_freq'] = freqs[pk[np.argmax(props['peak_heights'])]]
    else:
        f['spectral_peaks_mean_height'] = f['spectral_peaks_max_height'] = 0.0
        f['dominant_peak_freq'] = 0.0

    rms_db = librosa.amplitude_to_db(rms + 1e-10)
    f['db_mean'], f['db_max'] = np.mean(rms_db), np.max(rms_db)
    f['db_min'], f['db_std'] = np.min(rms_db), np.std(rms_db)
    f['db_range'] = f['db_max'] - f['db_min']
    thr = np.mean(rms_db) + np.std(rms_db)
    dbp = np.sum(rms_db > thr)
    f['db_peaks_count'], f['db_peaks_ratio'] = dbp, dbp / len(rms_db)

    pk_amp = np.max(np.abs(y))
    rms_t = np.sqrt(np.mean(y**2))
    cf = pk_amp / (rms_t + 1e-10)
    f['crest_factor'], f['crest_factor_db'] = cf, 20 * np.log10(cf + 1e-10)

    hm = (freqs >= 2000) & (freqs < 8000)
    vhm = freqs >= 8000
    lm = freqs < 500
    he = np.mean(S[hm, :]) if hm.any() else 0.0
    vhe = np.mean(S[vhm, :]) if vhm.any() else 0.0
    le = np.mean(S[lm, :]) if lm.any() else 1e-10
    f['high_freq_2k_8k'], f['very_high_freq_8k'] = he, vhe
    f['high_low_energy_ratio'] = (he + vhe) / (le + 1e-10)

    con = librosa.feature.spectral_contrast(y=y, sr=sr)
    f['spectral_contrast_mean'], f['spectral_contrast_std'] = np.mean(con), np.std(con)
    f['spectral_contrast_max'] = np.max(con)

    ro95 = librosa.feature.spectral_rolloff(y=y, sr=sr, roll_percent=0.95)[0]
    f['spectral_rolloff_95_mean'], f['spectral_rolloff_95_std'] = np.mean(ro95), np.std(ro95)

    rd = np.diff(rms)
    f['rms_variation_mean'], f['rms_variation_max'] = np.mean(np.abs(rd)), np.max(np.abs(rd))

    f['zcr_noise_mean'], f['zcr_noise_std'] = np.mean(zcr), np.std(zcr)
    f['zcr_noise_max'] = np.max(zcr)

    pe = np.sum(perc**2)
    he2 = np.sum(harm**2)
    te = pe + he2 + 1e-10
    f['percussive_ratio'] = pe / te
    f['perc_harm_ratio'] = pe / (he2 + 1e-10)

    return {k: float(v) for k, v in f.items()}


def process_file(filepath):
    """Traite un fichier WAV et retourne ses features."""
    import warnings
    warnings.filterwarnings("ignore")
    import librosa

    try:
        y, sr = librosa.load(str(filepath), sr=SR)
        if len(y) < SR * 0.5:
            return None
        y = librosa.util.normalize(y)
        feats = extract_all_features(y, sr)
        feats['nfile'] = Path(filepath).name
        return feats
    except Exception as e:
        return None


def main():
    parser = argparse.ArgumentParser(description="Extraction 225 features (parallele)")
    parser.add_argument("--input", type=str,
                        default=os.path.join(DATARMOR_WORK, "segments_bruyants"),
                        help="Dossier des segments WAV")
    parser.add_argument("--output", type=str,
                        default=os.path.join(DATARMOR_WORK, "segments_features.csv"),
                        help="CSV de sortie")
    parser.add_argument("--workers", type=int, default=48, help="Nombre de workers")
    args = parser.parse_args()

    print("=" * 70)
    print("  EXTRACTION 225 FEATURES - PARALLELE")
    print(f"  {args.workers} workers")
    print("=" * 70)

    input_dir = Path(args.input)
    wav_files = sorted(list(input_dir.glob("*.wav")) + list(input_dir.glob("*.WAV")))

    print(f"Fichiers: {len(wav_files)}")
    print(f"Sortie: {args.output}")
    print("=" * 70)

    results = []
    done = 0
    errors = 0

    with ProcessPoolExecutor(max_workers=args.workers) as executor:
        futures = {executor.submit(process_file, f): f for f in wav_files}

        for future in as_completed(futures):
            result = future.result()
            done += 1
            if result is not None:
                results.append(result)
            else:
                errors += 1

            if done % 500 == 0 or done == len(wav_files):
                print(f"  [{done}/{len(wav_files)}] {len(results)} ok, {errors} erreurs",
                      flush=True)

    df = pd.DataFrame(results)
    df.to_csv(args.output, index=False)

    print(f"\nTermine: {len(results)} fichiers -> {args.output}")
    print(f"Erreurs: {errors}")
    print(f"Features: {len(df.columns) - 1}")


if __name__ == "__main__":
    main()
