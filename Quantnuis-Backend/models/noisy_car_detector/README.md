# models/noisy_car_detector/

Modele de Daniel. Detecte si une voiture (deja identifiee par car_detector) est bruyante.

## Backends

Le modele supporte deux backends, avec priorite au CNN :

| Backend | Fichier artifact | F1 Score | Description |
|---|---|---|---|
| **CNN** (prioritaire) | `cnn_noisy_car.h5` + `cnn_config.json` | 0.994 | Conv2D sur mel-spectrogrammes |
| **MLP** (fallback) | `model.h5` + `scaler.pkl` + `features.txt` | 0.962 | Dense sur features manuelles (225) |

Si `cnn_noisy_car.h5` est present dans `artifacts/`, le CNN est utilise automatiquement.

## Fichiers

| Fichier | Description |
|---|---|
| `config.py` | Chemins, seuils (0.5), labels (BRUYANT/NORMAL), paths CNN |
| `model.py` | Classe NoisyCarDetector |
| `train.py` | Entrainement du MLP (features manuelles) |
| `optimize.py` | Optimisation Optuna des hyperparametres |
| `feature_extraction.py` | Extraction features -> `data/noisy_car_detector/features.csv` |

## NoisyCarDetector (model.py)

Herite de `BaseMLModel`. Override `load()` pour tenter le CNN d'abord.

### Methodes

| Methode | Description |
|---|---|
| `load()` | Tente `_load_cnn()`, sinon `super().load()` (MLP) |
| `_load_cnn()` | Charge cnn_noisy_car.h5 + cnn_config.json |
| `predict_file(audio_path, verbose)` | Dispatch vers `_predict_cnn()` ou `_predict_mlp()` |
| `_predict_cnn(audio_path)` | Mel-spectrogram (128 mels, 4s, 22050 Hz) -> Conv2D -> prediction |
| `_predict_mlp(audio_path)` | extract_base_features -> select -> predict |
| `get_model_info()` | Info + backend (CNN/MLP), F1, nb samples |

### Pipeline CNN interne

```
Audio (4s, 22050 Hz)
  -> librosa.load + pad/truncate
  -> librosa.util.normalize
  -> mel-spectrogram (128 mels, n_fft=2048, hop_length=512)
  -> power_to_db
  -> normalisation (X_mean, X_std du dataset)
  -> reshape (1, n_mels, time, 1)
  -> model.predict
  -> seuil 0.5 -> BRUYANT/NORMAL
```

### Config CNN (`cnn_config.json`)

```json
{
  "sr": 22050,
  "duration": 4.0,
  "n_mels": 128,
  "n_fft": 2048,
  "hop_length": 512,
  "X_mean": ...,
  "X_std": ...,
  "cv_f1_mean": 0.994,
  "n_samples": ...
}
```

## Commandes

```bash
# Extraction features
python -m models.noisy_car_detector.feature_extraction

# Entrainement MLP
python -m models.noisy_car_detector.train

# Optimisation hyperparametres
python -m models.noisy_car_detector.optimize --trials 50

# Prediction sur un fichier
python -m models.noisy_car_detector.model audio.wav
```
