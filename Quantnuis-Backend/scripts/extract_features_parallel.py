#!/usr/bin/env python3
"""EXTRACTION TURBO - Fix multiprocessing"""

if __name__ == "__main__":
    import multiprocessing as mp
    mp.set_start_method('spawn')  # AVANT tout autre import

    import os
    os.environ['NUMBA_DISABLE_JIT'] = '1'
    os.environ['OMP_NUM_THREADS'] = '1'

    import warnings
    warnings.filterwarnings('ignore')

    from pathlib import Path
    from concurrent.futures import ProcessPoolExecutor
    import numpy as np
    import pandas as pd

    SAMPLE_RATE = 22050
    N_MFCC = 40
    DATA_DIR = Path(__file__).parent.parent / "data" / "noisy_car_detector"
    SLICES_DIR = DATA_DIR / "slices"
    ANNOTATION_CSV = DATA_DIR / "annotation.csv"
    FEATURES_CSV = DATA_DIR / "features_all.csv"
    WORKERS = 16

    def run():
        print(f"🚀 TURBO EXTRACTION - {WORKERS} CORES")
        df = pd.read_csv(ANNOTATION_CSV)
        print(f"📁 {len(df)} fichiers")

        work = [(str(SLICES_DIR / r['nfile']), r['nfile'], r['label'], r.get('reliability', 1.0))
                for _, r in df.iterrows()]

        print("⚡ Lancement...", flush=True)

        results = []
        from extract_worker import process_file

        with ProcessPoolExecutor(max_workers=WORKERS) as ex:
            futures = [ex.submit(process_file, w) for w in work]
            for i, fut in enumerate(futures, 1):
                r = fut.result()
                if r:
                    results.append(r)
                if i % 50 == 0:
                    print(f"⚡ {i}/{len(work)}", flush=True)

        pd.DataFrame(results).to_csv(FEATURES_CSV, index=False)
        print(f"✅ {len(results)} extraits → {FEATURES_CSV}")

    run()
