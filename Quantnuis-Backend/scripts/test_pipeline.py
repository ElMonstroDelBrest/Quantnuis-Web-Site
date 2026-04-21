#!/usr/bin/env python3
"""
Test d'inférence de la pipeline complète.

Évalue la pipeline sur des échantillons représentatifs des 4 cas :
  - Voiture bruyante (label noisy=1)
  - Voiture normale  (label noisy=0)
  - Bruit / pas de voiture (label car=0)
  - Voiture détectée mais noisy_car indéterminé

Usage:
    cd Quantnuis-Backend
    python -m scripts.test_pipeline
    python -m scripts.test_pipeline --n 20       # 20 échantillons par classe
    python -m scripts.test_pipeline --verbose    # Affichage détaillé
"""

import sys
import argparse
import time
import numpy as np
import pandas as pd
from pathlib import Path

from shared import print_header, print_success, print_info, print_warning, print_error, Colors
from pipeline.orchestrator import Pipeline
from models.car_detector import config as car_cfg
from models.noisy_car_detector import config as noisy_cfg


def sample_files(annotation_csv: Path, slices_dir: Path, label: int, n: int,
                 min_reliability: int = 1, seed: int = 42) -> list:
    """Retourne n fichiers audio existants pour un label donné."""
    df = pd.read_csv(annotation_csv)
    df = df[(df['label'] == label) & (df['reliability'] >= min_reliability)]
    df = df.sample(frac=1, random_state=seed)

    files = []
    for _, row in df.iterrows():
        path = slices_dir / row['nfile']
        if path.exists():
            files.append(str(path))
        if len(files) >= n:
            break
    return files


def run_tests(n: int = 10, verbose: bool = False, min_reliability: int = 2):
    print_header("Test Pipeline Complète — Évaluation Inférence")

    # Charger la pipeline (une seule fois)
    print_info("Chargement des modèles...")
    t0 = time.time()
    pipeline = Pipeline()
    pipeline.load_models()
    load_time = time.time() - t0
    print_success(f"Modèles chargés en {load_time:.2f}s")
    print_info(f"  CarDetector backend: {'CRNN' if pipeline.car_detector.use_crnn else 'MLP'}")
    print()

    # =========================================================================
    # Cas 1 : Voitures bruyantes → attend car=True, noisy=True
    # =========================================================================
    print_header("CAS 1 — Voitures bruyantes (attendu: car=True, noisy=True)")
    noisy_files = sample_files(noisy_cfg.ANNOTATION_CSV, noisy_cfg.SLICES_DIR,
                               label=1, n=n, min_reliability=min_reliability)
    results_noisy = _evaluate(pipeline, noisy_files,
                              expected_car=True, expected_noisy=True, verbose=verbose)

    # =========================================================================
    # Cas 2 : Voitures normales → attend car=True, noisy=False
    # =========================================================================
    print_header("CAS 2 — Voitures normales (attendu: car=True, noisy=False)")
    normal_files = sample_files(noisy_cfg.ANNOTATION_CSV, noisy_cfg.SLICES_DIR,
                                label=0, n=n, min_reliability=min_reliability)
    results_normal = _evaluate(pipeline, normal_files,
                               expected_car=True, expected_noisy=False, verbose=verbose)

    # =========================================================================
    # Cas 3 : Bruit (pas de voiture) → attend car=False
    # =========================================================================
    print_header("CAS 3 — Bruit / pas de voiture (attendu: car=False)")
    bruit_files = sample_files(car_cfg.ANNOTATION_CSV, car_cfg.SLICES_DIR,
                               label=0, n=n, min_reliability=min_reliability)
    results_bruit = _evaluate(pipeline, bruit_files,
                              expected_car=False, expected_noisy=None, verbose=verbose)

    # =========================================================================
    # Cas 4 : Voitures (car_detector) → attend car=True
    # =========================================================================
    print_header("CAS 4 — Voitures (car_detector dataset) (attendu: car=True)")
    car_files = sample_files(car_cfg.ANNOTATION_CSV, car_cfg.SLICES_DIR,
                             label=1, n=n, min_reliability=min_reliability)
    results_car = _evaluate(pipeline, car_files,
                            expected_car=True, expected_noisy=None, verbose=verbose)

    # =========================================================================
    # Résumé global
    # =========================================================================
    _print_summary(results_noisy, results_normal, results_bruit, results_car, n)


def _evaluate(pipeline: Pipeline, files: list,
              expected_car: bool, expected_noisy, verbose: bool) -> dict:
    """Exécute l'inférence sur une liste de fichiers et retourne les métriques."""
    if not files:
        print_warning("Aucun fichier trouvé pour ce cas")
        return {'n': 0, 'car_correct': 0, 'noisy_correct': 0,
                'avg_time': 0, 'car_probs': [], 'noisy_probs': []}

    car_correct = 0
    noisy_correct = 0
    times = []
    car_probs = []
    noisy_probs = []
    errors = 0

    for path in files:
        try:
            t0 = time.time()
            result = pipeline.analyze(path, verbose=False)
            elapsed = time.time() - t0

            times.append(elapsed)
            car_probs.append(result.car_probability)

            car_ok = (result.car_detected == expected_car)
            if car_ok:
                car_correct += 1

            noisy_ok = True
            if expected_noisy is not None and result.car_detected:
                noisy_probs.append(result.noisy_probability or 0)
                noisy_ok = (result.is_noisy == expected_noisy)
                if noisy_ok:
                    noisy_correct += 1

            if verbose:
                car_sym = "✓" if car_ok else "✗"
                noisy_str = ""
                if expected_noisy is not None and result.car_detected:
                    noisy_sym = "✓" if noisy_ok else "✗"
                    noisy_str = f"  noisy={result.is_noisy}({result.noisy_probability:.2f}) {noisy_sym}"
                fname = Path(path).name[:30]
                print(f"  {car_sym} {fname:30s}  car={result.car_detected}({result.car_probability:.2f}){noisy_str}  [{elapsed:.2f}s]")

        except Exception as e:
            errors += 1
            if verbose:
                print_warning(f"  ERREUR {Path(path).name}: {e}")

    n = len(files)
    avg_time = np.mean(times) if times else 0

    car_acc = car_correct / n * 100
    noisy_n = len(noisy_probs)
    noisy_acc = noisy_correct / noisy_n * 100 if noisy_n > 0 else None

    # Affichage compact
    noisy_str = f"  noisy_acc={noisy_acc:.1f}%" if noisy_acc is not None else ""
    print_info(f"n={n}  car_acc={car_acc:.1f}%{noisy_str}  avg={avg_time:.2f}s/fichier  errors={errors}")

    return {
        'n': n,
        'car_correct': car_correct,
        'noisy_correct': noisy_correct,
        'noisy_n': noisy_n,
        'avg_time': avg_time,
        'car_probs': car_probs,
        'noisy_probs': noisy_probs,
        'errors': errors,
    }


def _print_summary(r_noisy, r_normal, r_bruit, r_car, n):
    print_header("RÉSUMÉ GLOBAL")

    rows = [
        ("Voitures bruyantes", r_noisy,  True,  True),
        ("Voitures normales",  r_normal, True,  False),
        ("Bruit (pas voiture)",r_bruit,  False, None),
        ("Voitures (car_det)", r_car,    True,  None),
    ]

    total_car_correct = 0
    total_car_n = 0
    total_noisy_correct = 0
    total_noisy_n = 0
    total_time = 0
    total_n = 0

    print(f"\n  {'Cas':<25} {'N':>4}  {'Car Acc':>8}  {'Noisy Acc':>10}  {'Avg(s)':>7}")
    print(f"  {'-'*65}")

    for name, r, exp_car, exp_noisy in rows:
        if r['n'] == 0:
            print(f"  {name:<25} {'N/A':>4}")
            continue

        car_acc = r['car_correct'] / r['n'] * 100
        noisy_acc_str = f"{r['noisy_correct']/r['noisy_n']*100:.1f}%" if r.get('noisy_n', 0) > 0 else "N/A"

        color = Colors.GREEN if car_acc >= 80 else (Colors.YELLOW if car_acc >= 60 else Colors.RED)
        print(f"  {name:<25} {r['n']:>4}  {color}{car_acc:>7.1f}%{Colors.END}  {noisy_acc_str:>10}  {r['avg_time']:>7.2f}s")

        total_car_correct += r['car_correct']
        total_car_n += r['n']
        total_noisy_correct += r['noisy_correct']
        total_noisy_n += r.get('noisy_n', 0)
        total_time += r['avg_time']
        total_n += 1

    print(f"  {'-'*65}")
    overall_car = total_car_correct / total_car_n * 100 if total_car_n > 0 else 0
    overall_noisy = total_noisy_correct / total_noisy_n * 100 if total_noisy_n > 0 else 0
    avg_t = total_time / total_n if total_n > 0 else 0

    car_color = Colors.GREEN if overall_car >= 80 else (Colors.YELLOW if overall_car >= 60 else Colors.RED)
    noisy_color = Colors.GREEN if overall_noisy >= 80 else (Colors.YELLOW if overall_noisy >= 60 else Colors.RED)

    print(f"\n  Car accuracy globale:   {car_color}{overall_car:.1f}%{Colors.END} ({total_car_correct}/{total_car_n})")
    print(f"  Noisy accuracy globale: {noisy_color}{overall_noisy:.1f}%{Colors.END} ({total_noisy_correct}/{total_noisy_n})")
    print(f"  Latence moyenne:        {avg_t:.2f}s / fichier")
    print()

    # Verdict
    if overall_car >= 80 and overall_noisy >= 75:
        print_success("Pipeline PRÊTE pour déploiement ✓")
    elif overall_car >= 65:
        print_warning("Pipeline fonctionnelle mais à améliorer")
    else:
        print_error("Pipeline insuffisante — retraining nécessaire")


def main():
    parser = argparse.ArgumentParser(description="Test inférence pipeline")
    parser.add_argument('--n', type=int, default=10, help="Fichiers par classe (défaut: 10)")
    parser.add_argument('--verbose', '-v', action='store_true', help="Affichage détaillé par fichier")
    parser.add_argument('--min-reliability', type=int, default=2, help="Fiabilité minimale des annotations")
    args = parser.parse_args()

    run_tests(n=args.n, verbose=args.verbose, min_reliability=args.min_reliability)


if __name__ == "__main__":
    main()
