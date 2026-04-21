# config/

Configuration centralisee du projet. Un seul fichier, un seul singleton.

## Structure

```
config/
└── settings.py    # Classe Settings + get_settings()
```

## Usage

```python
from config import get_settings
settings = get_settings()  # Singleton (lru_cache)
```

## Settings - Proprietes principales

### Detection d'environnement

| Propriete | Type | Description |
|---|---|---|
| `IS_LAMBDA` | bool | True si `AWS_LAMBDA_FUNCTION_NAME` est defini |
| `IS_DEBUG` | bool | True si `DEBUG=true` |

### Chemins

| Propriete | Type | Description |
|---|---|---|
| `BASE_DIR` | Path | Racine du projet |
| `TMP_DIR` | Path | `/tmp` sur Lambda, `{BASE_DIR}/tmp` en local |
| `DATA_DIR` | Path | `{BASE_DIR}/data` |
| `CAR_DETECTOR_DIR` | Path | `models/car_detector/artifacts/` |
| `NOISY_CAR_DETECTOR_DIR` | Path | `models/noisy_car_detector/artifacts/` |
| `CAR_MODEL_PATH` | Path | `.../artifacts/model.h5` |
| `CAR_SCALER_PATH` | Path | `.../artifacts/scaler.pkl` |
| `CAR_FEATURES_PATH` | Path | `.../artifacts/features.txt` |
| `NOISY_CAR_MODEL_PATH` | Path | Idem pour noisy_car |
| `NOISY_CAR_SCALER_PATH` | Path | Idem |
| `NOISY_CAR_FEATURES_PATH` | Path | Idem |

### Audio

| Attribut | Valeur | Description |
|---|---|---|
| `SAMPLE_RATE` | 22050 | Frequence d'echantillonnage (Hz) |
| `N_MFCC` | 40 | Nombre de coefficients MFCC |

### Seuils

| Attribut | Valeur | Description |
|---|---|---|
| `CAR_DETECTION_THRESHOLD` | 0.5 | Seuil detection voiture (prob > seuil = voiture) |
| `NOISY_THRESHOLD` | 0.5 | Seuil voiture bruyante |

### BDD

| Propriete | Description |
|---|---|
| `DB_PATH` | Priorite: env `DATABASE_PATH` > Lambda `/tmp/quantnuis.db` > local `data/quantnuis.db` |
| `DATABASE_URL` | `sqlite:///{DB_PATH}` |

### S3

| Attribut | Defaut | Env var |
|---|---|---|
| `S3_BUCKET_NAME` | `quantnuis-db-bucket` | `DB_BUCKET_NAME` |
| `S3_AUDIO_BUCKET_NAME` | `quantnuis-audio-bucket` | `AUDIO_BUCKET_NAME` |
| `S3_PRESIGNED_URL_EXPIRATION` | 3600 (1h) | `S3_PRESIGNED_URL_EXPIRATION` |

### Securite

| Propriete | Description |
|---|---|
| `SECRET_KEY` | Env `SECRET_KEY`. Si absent: genere une cle temporaire (warning) |
| `ALGORITHM` | `HS256` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | 1440 (24h). Env: `ACCESS_TOKEN_EXPIRE_MINUTES` |

### Entrainement

| Attribut | Valeur | Description |
|---|---|---|
| `TRAINING_EPOCHS` | 60 | Nombre d'epochs |
| `TRAINING_BATCH_SIZE` | 16 | Taille des batchs |
| `SMOTE_K_NEIGHBORS` | 3 | Voisins SMOTE (petit dataset) |
| `TEST_SIZE` | 0.2 | 20% test |
| `TOP_FEATURES_COUNT` | 12 | Features selectionnees apres analyse |
