# Quantnuis — Backend

Système de détection de véhicules bruyants par analyse audio. Pipeline en cascade à deux modèles IA.

[![Python 3.11](https://img.shields.io/badge/Python-3.11-blue.svg)](https://www.python.org/downloads/)
[![TensorFlow 2.15](https://img.shields.io/badge/TensorFlow-2.15-orange.svg)](https://www.tensorflow.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.109+-green.svg)](https://fastapi.tiangolo.com/)

---

## Pipeline

```
Fichier audio
     |
     v
Extraction de features (MFCC, spectral, temporel — ~180 features, top 40 sélectionnées)
     |
     v
Modele 1 : CarDetector      — "Y a-t-il une voiture ?"
     |
     +-- Non --> Fin : aucun vehicule detecte
     |
     +-- Oui -->
          |
          v
     Modele 2 : NoisyCarDetector  — "Cette voiture est-elle bruyante ?"
          |
          +-- Non --> Vehicule normal
          +-- Oui --> Vehicule bruyant
```

**Note :** CarDetector est le modèle du collègue — ne pas modifier. NoisyCarDetector est le modèle de Daniel.

---

## Structure

```
Quantnuis-Backend/
├── api/
│   ├── ec2_api/        # API stateful (auth, données, annotations) — déployée sur EC2
│   └── lambda_api/     # API stateless (/predict) — déployée sur AWS Lambda
├── config/
│   └── settings.py     # Configuration centralisée
├── data/               # Données d'entraînement (non versionné)
├── data_management/    # Outils d'ajout et découpage de slices audio
├── database/           # ORM SQLAlchemy, schemas Pydantic, gestion S3
├── models/
│   ├── car_detector/           # Modèle 1 (collègue)
│   └── noisy_car_detector/     # Modèle 2 (Daniel)
├── pipeline/
│   └── orchestrator.py         # Chaînage des deux modèles
├── scripts/            # Scripts d'administration et migration
├── shared/             # Utilitaires partagés (audio_utils, logger)
├── deployment/         # Config EC2 (nginx, systemd)
├── Dockerfile          # Image Lambda
├── docker-compose.yml
└── requirements.txt
```

---

## Installation

**Prérequis :** Python 3.11 (TensorFlow 2.15 est incompatible avec Python 3.12), FFmpeg

```bash
python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Avec Docker :

```bash
docker-compose up
# API disponible sur http://localhost:8000
```

---

## Entraînement

```bash
# 1. Extraire les features
python -m models.noisy_car_detector.feature_extraction

# 2. Entraîner
python -m models.noisy_car_detector.train
```

Les fichiers générés dans `models/noisy_car_detector/artifacts/` :
- `model.h5` — modèle TensorFlow/Keras
- `scaler.pkl` — StandardScaler
- `features.txt` — liste des features sélectionnées

---

## Données d'entraînement

```
data/noisy_car_detector/
├── slices/          # Fichiers .wav (3-60 s recommandé)
├── annotation.csv   # Labels (nfile, length, label, reliability)
└── features.csv     # Généré automatiquement
```

Labels pour `noisy_car_detector` : `0` = voiture normale, `1` = voiture bruyante

```bash
# Ajouter des slices
python -m data_management.slice_manager -m noisy_car -a add -s /chemin/vers/audios

# Découper un enregistrement long avec annotations temporelles
python -m data_management.slicing -m noisy_car audio_long.wav annotations.csv
```

---

## Utilisation

```bash
# Pipeline complet en ligne de commande
python -m pipeline.orchestrator audio.wav

# Démarrer l'API
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
# Swagger : http://localhost:8000/docs
```

**Réponse `/predict` :**

```json
{
  "hasNoisyVehicle": true,
  "carDetected": true,
  "confidence": 92.1,
  "message": "Vehicule bruyant detecte (confiance: 92.1%)"
}
```

---

## Déploiement AWS Lambda

```bash
# Build et push ECR
docker build -t quantnuis-api .
aws ecr get-login-password --region eu-west-3 | docker login --username AWS --password-stdin <account_id>.dkr.ecr.eu-west-3.amazonaws.com
docker tag quantnuis-api:latest <account_id>.dkr.ecr.eu-west-3.amazonaws.com/quantnuis-api:latest
docker push <account_id>.dkr.ecr.eu-west-3.amazonaws.com/quantnuis-api:latest
```

Variables d'environnement Lambda requises :

| Variable | Description |
|----------|-------------|
| `SECRET_KEY` | Clé secrète JWT (changer en production) |
| `DB_BUCKET_NAME` | Bucket S3 pour la base de données |

La Lambda nécessite 1024 MB de mémoire et un timeout de 60 s minimum.

---

## Configuration

`config/settings.py` centralise tous les paramètres. Variables d'environnement :

| Variable | Défaut | Description |
|----------|--------|-------------|
| `DEBUG` | `false` | Logs détaillés |
| `SECRET_KEY` | dev key | **Changer en production** |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `30` | Durée du JWT |
| `DB_BUCKET_NAME` | `quantnuis-db-bucket` | Bucket S3 |

Paramètres audio clés : `SAMPLE_RATE=22050`, `N_MFCC=40`, `TOP_FEATURES_COUNT=12`, `CAR_DETECTION_THRESHOLD=0.5`

---

## Troubleshooting

**`No module named 'tensorflow'`** → `pip install tensorflow==2.15.0`

**`Could not load dynamic library 'libcuda.so'`** → Normal sans GPU, TensorFlow fonctionne sur CPU.

**`NUMBA_CACHE_DIR not writable`** → `export NUMBA_CACHE_DIR=/tmp`

**Lambda ne démarre pas** → Vérifier mémoire (1024 MB min), permissions IAM (S3 + CloudWatch), logs CloudWatch.
