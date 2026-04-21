# scripts/

Scripts utilitaires pour l'administration, la migration, et l'analyse.

## Structure

```
scripts/
├── benchmark.py                 # Benchmark 10 modeles sklearn (deplace depuis shared/)
├── benchmark_cnn.py             # Benchmark CNN mel-spectrogrammes (deplace depuis shared/)
├── test_pipeline.py             # Evaluation inference pipeline
├── report_pipeline.py           # Rapport graphique pipeline
├── make_admin.py                # Promouvoir un user en admin
├── migrate_sqlite_to_postgres.py # Migration BDD SQLite -> PostgreSQL
├── export_rf_model.py           # Export modele Random Forest
├── data_mining.py               # Data mining sur les features
├── active_learning.py           # Active learning pour ameliorer le dataset
├── extract_features_parallel.py # Extraction features en parallele (multiprocessing)
├── extract_worker.py            # Worker pour l'extraction parallele
├── datarmor/                    # Scripts pour cluster HPC Datarmor
│   ├── datarmor_extract_features.py
│   ├── datarmor_extract_normal.py
│   ├── datarmor_mining.py
│   ├── datarmor_rescore.py
│   ├── datarmor_review_retrain.py
│   └── datarmor_train_cnn.py
└── outputs/                     # Fichiers generes (gitignore)
    └── rf_mining_model.pkl
```

## Scripts principaux

### benchmark.py

Compare 10 modeles sklearn (RF, SVM, KNN, LR, etc.) avec cross-validation.

```bash
python -m scripts.benchmark --model car_detector              # Toutes features
python -m scripts.benchmark --model car_detector --optimized  # Features optimisees
```

### benchmark_cnn.py

Evalue le CNN NoisyCarDetector pre-entraine et compare avec sklearn.

```bash
python -m scripts.benchmark_cnn                   # CNN seul
python -m scripts.benchmark_cnn --compare          # + comparaison sklearn
```

### test_pipeline.py + report_pipeline.py

Evaluation du pipeline d'inference et generation de rapports graphiques.

```bash
python -m scripts.test_pipeline
python -m scripts.report_pipeline
```

### make_admin.py

Promouvoir un utilisateur en administrateur via la BDD.

```bash
python scripts/make_admin.py
```

### migrate_sqlite_to_postgres.py

Migration de la base SQLite locale vers PostgreSQL (EC2 prod).

```bash
python scripts/migrate_sqlite_to_postgres.py
```

### extract_features_parallel.py + extract_worker.py

Extraction de features en parallele avec multiprocessing.
`extract_worker.py` est le worker appele par le script principal.

```bash
python scripts/extract_features_parallel.py
```

### data_mining.py

Analyse exploratoire des features extraites.

### active_learning.py

Pipeline d'active learning pour identifier les samples les plus informatifs.

### export_rf_model.py

Export d'un modele Random Forest entraine (sauvegarde dans `outputs/`).

## datarmor/

Scripts adaptes pour execution sur le cluster HPC Datarmor (IFREMER).
Versions adaptees des scripts principaux pour l'environnement HPC.

## outputs/

Dossier pour les fichiers generes par les scripts. Gitignore.
