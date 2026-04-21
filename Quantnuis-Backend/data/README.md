# data/

Donnees d'entrainement et base de donnees locale.

## Structure

```
data/
├── car_detector/                  # Donnees modele 1 (NE PAS MODIFIER)
│   ├── slices/                    # Fichiers audio decoupes (.wav) [gitignore]
│   ├── annotation.csv             # Labels : nfile, length, label (0/1), reliability
│   ├── features.csv               # Features extraites [gitignore]
│   ├── features_all.csv           # Toutes les features (~225) [gitignore]
│   └── features_optimized.csv     # Features selectionnees [gitignore]
├── noisy_car_detector/            # Donnees modele 2 (modele de Daniel)
│   ├── slices/                    # Fichiers audio decoupes (.wav) [gitignore]
│   ├── annotation.csv             # Labels : nfile, length, label (0=normal, 1=bruyant), reliability
│   ├── features.csv               # Features extraites [gitignore]
│   ├── features_all.csv           # Toutes les features (~225) [gitignore]
│   └── features_optimized.csv     # Features selectionnees [gitignore]
├── annotation_requests/           # Fichiers audio des demandes d'annotation (via API)
└── quantnuis.db                   # Base SQLite locale [gitignore]
```

## Format annotation.csv

```csv
nfile,length,label,reliability
slice_001.wav,38,1,3
slice_002.wav,13,0,3
```

| Colonne | Type | Description |
|---|---|---|
| `nfile` | str | Nom du fichier (slice_XXX.wav) |
| `length` | int | Duree en secondes |
| `label` | int | 0 ou 1 (signification depend du modele) |
| `reliability` | int | Fiabilite de l'annotation (1-5, defaut: 3) |

### Labels par modele

| Modele | Label 0 | Label 1 |
|---|---|---|
| car_detector | Pas de voiture | Voiture |
| noisy_car_detector | Voiture normale | Voiture bruyante |

## Workflow d'ajout de donnees

1. Enregistrer ou obtenir un audio long
2. Annoter avec un CSV (Start, End, Label, Reliability)
3. Decouper : `python -m data_management.slicing -m noisy_car audio.wav annotations.csv`
4. Verifier : `python -m data_management.slice_manager -m noisy_car -a status`
5. Extraire features : `python -m models.noisy_car_detector.feature_extraction`
6. Entrainer : `python -m models.noisy_car_detector.train`
