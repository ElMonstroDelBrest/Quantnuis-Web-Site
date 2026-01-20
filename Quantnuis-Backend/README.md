# 🚗💨 Quantnuis

**Système intelligent de détection de véhicules bruyants par analyse audio**

[![Python 3.11](https://img.shields.io/badge/Python-3.11-blue.svg)](https://www.python.org/downloads/)
[![TensorFlow 2.15](https://img.shields.io/badge/TensorFlow-2.15-orange.svg)](https://www.tensorflow.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.109+-green.svg)](https://fastapi.tiangolo.com/)
[![AWS Lambda](https://img.shields.io/badge/AWS-Lambda-yellow.svg)](https://aws.amazon.com/lambda/)

---

## 📖 Description

Quantnuis utilise une architecture à **deux modèles IA en cascade** pour détecter les véhicules bruyants dans des enregistrements audio :

1. **CarDetector** - Détecte la présence d'un véhicule
2. **NoisyCarDetector** - Analyse si le véhicule détecté est bruyant

Cette approche en deux étapes permet une meilleure précision et évite les faux positifs.

---

## 🏗️ Architecture du Pipeline

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           PIPELINE D'ANALYSE                                │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│    🎵 Fichier Audio (.wav, .mp3, .flac...)                                  │
│              │                                                              │
│              ▼                                                              │
│    ┌───────────────────────────────────────┐                                │
│    │  📊 Extraction de Features (~100)     │                                │
│    │  • MFCC (40 coefficients)             │                                │
│    │  • Spectral (centroid, bandwidth...)  │                                │
│    │  • Temporel (RMS, ZCR)                │                                │
│    │  • Chroma (12 notes)                  │                                │
│    └──────────────────┬────────────────────┘                                │
│                       │                                                     │
│                       ▼                                                     │
│    ┌───────────────────────────────────────┐                                │
│    │  🚗 MODÈLE 1 : CarDetector            │                                │
│    │  "Y a-t-il une voiture ?"             │                                │
│    │  • Dense(64) → Dropout → Dense(32)    │                                │
│    │  • Sortie : Sigmoid (0-1)             │                                │
│    └──────────────────┬────────────────────┘                                │
│                       │                                                     │
│              ┌────────┴────────┐                                            │
│              ▼                 ▼                                            │
│         Probabilité       Probabilité                                       │
│          < 0.5              ≥ 0.5                                           │
│              │                 │                                            │
│              ▼                 ▼                                            │
│    ┌─────────────────┐  ┌───────────────────────────────────────┐           │
│    │  ❌ PAS DE      │  │  🔊 MODÈLE 2 : NoisyCarDetector       │           │
│    │     VOITURE     │  │  "Cette voiture est-elle bruyante ?"  │           │
│    │                 │  │  • Dense(64) → Dropout → Dense(32)    │           │
│    │  FIN            │  │  • Sortie : Sigmoid (0-1)             │           │
│    └─────────────────┘  └──────────────────┬────────────────────┘           │
│                                            │                                │
│                               ┌────────────┴────────────┐                   │
│                               ▼                         ▼                   │
│                     ┌─────────────────┐       ┌─────────────────┐           │
│                     │  ✅ NORMAL      │       │  ⚠️ BRUYANT     │           │
│                     │  ~60-70 dB      │       │  ~90-100 dB     │           │
│                     └─────────────────┘       └─────────────────┘           │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 📁 Structure du Projet

```
Quantnuis/
│
├── 📂 config/                          # ⚙️ Configuration centralisée
│   ├── __init__.py
│   └── settings.py                     # Paramètres (chemins, seuils, Lambda)
│
├── 📂 shared/                          # 🔧 Utilitaires partagés
│   ├── __init__.py
│   ├── colors.py                       # Codes ANSI pour terminal coloré
│   ├── logger.py                       # print_header, print_success, etc.
│   └── audio_utils.py                  # Extraction de ~100 features audio
│
├── 📂 models/                          # 🤖 Modèles IA
│   ├── __init__.py
│   ├── base_model.py                   # Classe abstraite de base
│   │
│   ├── 📂 car_detector/                # 🚗 MODÈLE 1 : Détection voiture
│   │   ├── __init__.py
│   │   ├── config.py                   # Configuration spécifique
│   │   ├── feature_extraction.py       # Extraction des features
│   │   ├── train.py                    # Entraînement
│   │   ├── model.py                    # Classe CarDetector
│   │   └── 📂 artifacts/               # Fichiers générés
│   │       ├── model.h5                # Modèle TensorFlow
│   │       ├── scaler.pkl              # StandardScaler
│   │       └── features.txt            # Liste des features
│   │
│   └── 📂 noisy_car_detector/          # 🔊 MODÈLE 2 : Voiture bruyante
│       ├── __init__.py
│       ├── config.py
│       ├── feature_extraction.py
│       ├── train.py
│       ├── model.py                    # Classe NoisyCarDetector
│       └── 📂 artifacts/
│
├── 📂 database/                        # 💾 Couche de données
│   ├── __init__.py
│   ├── connection.py                   # SQLAlchemy engine & session
│   ├── models.py                       # ORM (User, CarDetection, NoisyCarAnalysis)
│   ├── schemas.py                      # Pydantic schemas
│   └── s3_manager.py                   # Persistance SQLite sur S3
│
├── 📂 data_management/                 # 📊 Gestion des données
│   ├── __init__.py
│   ├── slice_manager.py                # Ajouter/gérer les slices audio
│   └── slicing.py                      # Découper des audios longs
│
├── 📂 pipeline/                        # 🔄 Orchestration
│   ├── __init__.py
│   └── orchestrator.py                 # Chaînage des 2 modèles
│
├── 📂 api/                             # 🌐 API REST
│   ├── __init__.py
│   └── main.py                         # FastAPI + Mangum (Lambda)
│
├── 📂 data/                            # 📁 Données (non versionné)
│   ├── 📂 car_detector/
│   │   ├── slices/                     # Fichiers .wav
│   │   ├── annotation.csv              # Labels
│   │   └── features.csv                # Features extraites
│   └── 📂 noisy_car_detector/
│       ├── slices/
│       ├── annotation.csv
│       └── features.csv
│
├── requirements.txt                    # Dépendances Python
├── Dockerfile                          # Image AWS Lambda
├── Dockerfile.dev                      # Image développement
├── docker-compose.yml                  # Orchestration Docker
├── .gitignore
└── README.md
```

---

## 🚀 Installation

### Prérequis

| Outil | Version | Notes |
|-------|---------|-------|
| Python | 3.11 | ⚠️ Pas 3.12 (incompatible TensorFlow 2.15) |
| FFmpeg | Dernière | Pour le traitement audio |
| Docker | Optionnel | Pour le déploiement |

### Installation locale

```bash
# 1. Cloner et accéder au projet
cd ~/Quantnuis

# 2. Créer l'environnement virtuel
python3.11 -m venv venv

# 3. Activer l'environnement
source venv/bin/activate        # Linux/Mac
# ou
venv\Scripts\activate           # Windows

# 4. Installer les dépendances
pip install --upgrade pip
pip install -r requirements.txt

# 5. Vérifier l'installation
python -c "import tensorflow as tf; print(f'TensorFlow {tf.__version__}')"
```

### Installation avec Docker

```bash
# Développement avec hot-reload
docker-compose up

# → API disponible sur http://localhost:8000
# → Documentation Swagger : http://localhost:8000/docs
```

---

## 📊 Préparation des Données

### Format des données

Chaque modèle nécessite :

```
data/<nom_modele>/
├── slices/              # Fichiers audio .wav (3-60 secondes recommandé)
│   ├── slice_001.wav
│   ├── slice_002.wav
│   └── ...
├── annotation.csv       # Labels
└── features.csv         # Généré automatiquement
```

**Format de `annotation.csv` :**

```csv
nfile,length,label,reliability
slice_001.wav,15,1,3
slice_002.wav,22,0,3
```

| Colonne | Description |
|---------|-------------|
| `nfile` | Nom du fichier audio |
| `length` | Durée en secondes |
| `label` | Classe (voir ci-dessous) |
| `reliability` | Fiabilité 1-3 (optionnel) |

### Labels par modèle

| Modèle | Label 0 | Label 1 |
|--------|---------|---------|
| **car_detector** | Pas de voiture | Voiture présente |
| **noisy_car_detector** | Voiture normale | Voiture bruyante |

### Ajouter des données

```bash
# Modèle 1 - Détection de voiture
python -m data_management.slice_manager -m car -a add -s /chemin/vers/audios

# Modèle 2 - Voiture bruyante (⚠️ uniquement des audios AVEC voiture !)
python -m data_management.slice_manager -m noisy_car -a add -s /chemin/vers/audios

# Voir le statut
python -m data_management.slice_manager -m car -a status
python -m data_management.slice_manager -m noisy_car -a status
```

### Découper un audio long

Si vous avez un enregistrement long avec des annotations :

```bash
# Format du CSV d'annotations temporelles :
# Start,End,Label,Reliability
# 00:09:34,00:10:12,1,3
# 00:11:30,00:11:43,0,3

python -m data_management.slicing -m car audio_long.wav annotations.csv
```

---

## 🏋️ Entraînement des Modèles

### Étape 1 : Extraction des features

Extrait ~100 caractéristiques audio par fichier :

```bash
# Modèle 1
python -m models.car_detector.feature_extraction

# Modèle 2
python -m models.noisy_car_detector.feature_extraction

# Options disponibles :
#   status    → Voir le statut
#   --force   → Réextraire tout
#   --label N → Extraire uniquement le label N
```

**Features extraites :**

| Catégorie | Nombre | Description |
|-----------|--------|-------------|
| MFCC | 80 | Empreinte sonore (40 × mean/std) |
| Spectral | 12 | Centroid, bandwidth, rolloff, flatness, contrast |
| Temporel | 4 | RMS, ZCR (volume, passages par zéro) |
| Harmonic/Percussive | 5 | Séparation composantes musicales/bruits |
| Chroma | 14 | Énergie par note musicale |
| Autres | 3 | Tempo, énergie, amplitude max |

### Étape 2 : Entraînement

```bash
# Modèle 1 - Détection de voiture
python -m models.car_detector.train

# Modèle 2 - Voiture bruyante
python -m models.noisy_car_detector.train
```

**Ce que fait l'entraînement :**

1. Charge les features depuis `features.csv`
2. Analyse l'importance des features (Random Forest)
3. Sélectionne les 12 meilleures features
4. Applique SMOTE si déséquilibre de classes
5. Split train/test (80/20)
6. Standardise les données
7. Entraîne le réseau de neurones (60 epochs)
8. Sauvegarde le modèle, scaler et liste des features

**Fichiers générés :**

```
models/<nom>/artifacts/
├── model.h5          # Modèle TensorFlow/Keras
├── scaler.pkl        # StandardScaler (normalisation)
└── features.txt      # Liste des 12 features utilisées
```

---

## 🎯 Utilisation

### Ligne de commande

```bash
# Pipeline complet (recommandé)
python -m pipeline.orchestrator audio.wav

# Résultat :
# ┌───────────────────────────────────────┐
# │   ⚠️  VOITURE BRUYANTE              │
# │   Détection voiture: 87.3%           │
# │   Analyse bruit:     92.1%           │
# │   Niveau estimé:     ~95 dB          │
# └───────────────────────────────────────┘
```

```bash
# Modèle 1 seul
python -m models.car_detector.model audio.wav

# Modèle 2 seul (⚠️ requiert un audio avec voiture !)
python -m models.noisy_car_detector.model audio.wav
```

### API REST

```bash
# Démarrer le serveur
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000

# Ou avec Docker
docker-compose up
```

**Documentation interactive :**
- Swagger UI : http://localhost:8000/docs
- ReDoc : http://localhost:8000/redoc

### Endpoints API

| Endpoint | Méthode | Auth | Description |
|----------|---------|------|-------------|
| `/health` | GET | ❌ | Vérification santé de l'API |
| `/predict` | POST | Optionnel | Analyse audio (format simplifié) |
| `/predict/detailed` | POST | Optionnel | Analyse audio (format détaillé) |
| `/register` | POST | ❌ | Inscription nouvel utilisateur |
| `/token` | POST | ❌ | Authentification (obtenir JWT) |
| `/users/me` | GET | ✅ | Infos utilisateur connecté |
| `/stats` | GET | ✅ | Statistiques utilisateur |
| `/history` | GET | ✅ | Historique des analyses |

### Exemples d'utilisation de l'API

**Analyser un fichier audio :**

```bash
curl -X POST "http://localhost:8000/predict" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@audio.wav"
```

**Réponse (format simplifié) :**

```json
{
  "hasNoisyVehicle": true,
  "confidence": 0.92,
  "maxDecibels": 95,
  "message": "🚗💨 VOITURE BRUYANTE détectée ! (confiance: 92.1%)"
}
```

**Réponse détaillée (`/predict/detailed`) :**

```json
{
  "car_detected": true,
  "car_confidence": 87.3,
  "car_probability": 0.873,
  "is_noisy": true,
  "noisy_confidence": 92.1,
  "noisy_probability": 0.921,
  "estimated_db": 95,
  "message": "🚗💨 VOITURE BRUYANTE détectée !"
}
```

**Authentification :**

```bash
# 1. Inscription
curl -X POST "http://localhost:8000/register" \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com", "password": "secret123"}'

# 2. Connexion
curl -X POST "http://localhost:8000/token" \
  -d "username=user@example.com&password=secret123"

# Réponse : {"access_token": "eyJ...", "token_type": "bearer"}

# 3. Utiliser le token
curl -X GET "http://localhost:8000/stats" \
  -H "Authorization: Bearer eyJ..."
```

---

## ☁️ Déploiement AWS Lambda

### 1. Construire l'image Docker

```bash
docker build -t quantnuis-api .
```

### 2. Pousser sur Amazon ECR

```bash
# Variables
AWS_ACCOUNT_ID=123456789012
AWS_REGION=eu-west-1

# Connexion à ECR
aws ecr get-login-password --region $AWS_REGION | \
  docker login --username AWS --password-stdin \
  $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com

# Créer le repository (si nécessaire)
aws ecr create-repository --repository-name quantnuis-api

# Tagger et pousser
docker tag quantnuis-api:latest \
  $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/quantnuis-api:latest

docker push \
  $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/quantnuis-api:latest
```

### 3. Créer la fonction Lambda

```bash
aws lambda create-function \
  --function-name quantnuis-api \
  --package-type Image \
  --code ImageUri=$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/quantnuis-api:latest \
  --role arn:aws:iam::$AWS_ACCOUNT_ID:role/lambda-execution-role \
  --timeout 60 \
  --memory-size 1024
```

### 4. Variables d'environnement Lambda

| Variable | Description | Exemple |
|----------|-------------|---------|
| `SECRET_KEY` | Clé secrète JWT | `ma_cle_super_secrete_32chars` |
| `DB_BUCKET_NAME` | Bucket S3 pour BDD | `quantnuis-db-bucket` |
| `DEBUG` | Mode debug | `false` |

### 5. Permissions IAM

La fonction Lambda nécessite :
- `s3:GetObject` et `s3:PutObject` sur le bucket de la BDD
- CloudWatch Logs pour les logs

---

## ⚙️ Configuration

Toute la configuration est centralisée dans `config/settings.py`.

### Variables d'environnement

| Variable | Défaut | Description |
|----------|--------|-------------|
| `DEBUG` | `false` | Active les logs détaillés |
| `SECRET_KEY` | (dev key) | **⚠️ CHANGER EN PRODUCTION** |
| `ALGORITHM` | `HS256` | Algorithme JWT |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `30` | Durée validité token |
| `DB_BUCKET_NAME` | `quantnuis-db-bucket` | Bucket S3 |

### Paramètres des modèles

| Paramètre | Défaut | Description |
|-----------|--------|-------------|
| `SAMPLE_RATE` | 22050 | Fréquence d'échantillonnage |
| `N_MFCC` | 40 | Nombre de coefficients MFCC |
| `TOP_FEATURES_COUNT` | 12 | Features sélectionnées |
| `TRAINING_EPOCHS` | 60 | Epochs d'entraînement |
| `TRAINING_BATCH_SIZE` | 16 | Taille des batchs |
| `CAR_DETECTION_THRESHOLD` | 0.5 | Seuil détection voiture |
| `NOISY_THRESHOLD` | 0.5 | Seuil détection bruit |

---

## 🐛 Troubleshooting

### Erreur : "No module named 'tensorflow'"

```bash
pip install tensorflow==2.15.0
```

### Erreur : "Could not load dynamic library 'libcuda.so'"

Normal si pas de GPU. TensorFlow fonctionne sur CPU par défaut.

### Erreur : "NUMBA_CACHE_DIR not writable"

```bash
export NUMBA_CACHE_DIR=/tmp
```

### Les prédictions sont mauvaises

1. Vérifiez que vous avez assez de données (>50 par classe)
2. Vérifiez l'équilibre des classes
3. Augmentez les epochs d'entraînement
4. Vérifiez que les audios sont de bonne qualité

### L'API ne démarre pas sur Lambda

- Vérifiez que la mémoire est suffisante (1024 MB minimum)
- Vérifiez les permissions IAM
- Consultez les logs CloudWatch

---

## 📈 Performance

| Métrique | Modèle 1 | Modèle 2 |
|----------|----------|----------|
| Précision (test) | ~85-95% | ~85-95% |
| Temps d'inférence | ~500ms | ~500ms |
| Mémoire | ~500MB | ~500MB |

*Les performances dépendent de la qualité et quantité des données d'entraînement.*

---

## 🤝 Contribution

1. Créer une branche : `git checkout -b feature/ma-feature`
2. Commiter : `git commit -m "Ajout de ma feature"`
3. Pousser : `git push origin feature/ma-feature`
4. Créer une Pull Request

---

## 📄 Licence

Projet privé - Tous droits réservés.

---

<p align="center">
  <strong>Fait avec ❤️ pour lutter contre les nuisances sonores</strong>
</p>
