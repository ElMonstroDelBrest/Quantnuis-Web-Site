# models/

Modeles de machine learning pour la detection de vehicules bruyants.

## Structure

```
models/
├── base_model.py              # Classe abstraite commune (BaseMLModel)
├── car_detector/              # Modele 1 : detection voiture (NE PAS MODIFIER)
│   ├── config.py              # Chemins, seuils, labels
│   ├── model.py               # CarDetector (herite BaseMLModel)
│   ├── train.py               # Script d'entrainement
│   ├── feature_extraction.py  # Extraction features -> CSV
│   └── artifacts/             # model.h5, scaler.pkl, features.txt
└── noisy_car_detector/        # Modele 2 : voiture bruyante (modele de Daniel)
    ├── config.py              # Chemins, seuils, labels, paths CNN
    ├── model.py               # NoisyCarDetector (CNN + MLP fallback)
    ├── train.py               # Script d'entrainement MLP
    ├── optimize.py            # Optimisation hyperparametres (Optuna)
    ├── feature_extraction.py  # Extraction features -> CSV
    └── artifacts/             # model.h5, scaler.pkl, features.txt, cnn_noisy_car.h5, cnn_config.json
```

## IMPORTANT

**`car_detector/` est le modele du collegue de Daniel. NE PAS MODIFIER sans son accord.**

**`noisy_car_detector/` est le modele de Daniel. Modifications libres.**

## base_model.py - BaseMLModel (ABC)

Classe abstraite dont heritent les deux modeles.

### Proprietes abstraites (a implementer)

| Propriete | Type | Description |
|---|---|---|
| `model_path` | Path | Chemin vers model.h5 |
| `scaler_path` | Path | Chemin vers scaler.pkl |
| `features_path` | Path | Chemin vers features.txt |
| `threshold` | float | Seuil de classification (0.5) |
| `positive_label` | str | Label classe positive |
| `negative_label` | str | Label classe negative |

### Methodes

| Methode | Signature | Description |
|---|---|---|
| `load()` | `() -> bool` | Charge model.h5 + scaler.pkl + features.txt |
| `ensure_loaded()` | `() -> bool` | Charge si pas deja fait |
| `predict_features(features)` | `(dict) -> (label, confidence, probability)` | Prediction depuis features extraites |
| `predict_file(audio_path)` | `(str) -> (label, confidence, probability)` | **Abstrait** - prediction depuis fichier audio |
| `is_loaded` | property -> bool | Modele charge ? |
| `n_features` | property -> int | Nombre de features |
| `get_model_info()` | `() -> dict` | Info du modele |

### Retour des predictions

Tuple `(label: str, confidence: float, probability: float)` :
- `label` : VOITURE/PAS_VOITURE ou BRUYANT/NORMAL
- `confidence` : pourcentage 0-100
- `probability` : sigmoid brut 0-1
