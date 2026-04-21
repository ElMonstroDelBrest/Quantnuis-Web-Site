# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## IMPORTANT - Model Ownership

**NE PAS MODIFIER car_detector** - C'est le modèle du collègue de Daniel.

**noisy_car_detector** - C'est le modèle de Daniel (véhicules bruyants/rapides). Seul ce modèle peut être modifié.

## Project Overview

Quantnuis is a noisy vehicle detection system using a **two-model cascade pipeline**:
1. **CarDetector** - Detects vehicle presence in audio (**NE PAS MODIFIER**)
2. **NoisyCarDetector** - Analyzes if detected vehicle is noisy (**Modèle de Daniel**)

Stack: FastAPI (Python 3.11) + TensorFlow 2.15 + SQLite/PostgreSQL.

## Architecture Cloud (Production)

```
EC2 (quantnuis-api-ec2, t3.micro, eu-west-3)
  - API stateful: auth, admin, annotations, S3 audio, gamification
  - PostgreSQL, Nginx reverse proxy, systemd service
  - IP: 15.236.239.107 (PAS d'Elastic IP)
  - Code: api/ec2_api/
  - Deps: requirements-ec2.txt (leger, pas de TensorFlow)

Lambda (quantnuis-api, eu-west-3, ECR Docker)
  - API stateless: /predict uniquement (modele IA)
  - TensorFlow 2.15, pipeline cascade
  - Code: api/lambda_api/
  - Deps: requirements.txt (complet avec TF)

S3 Buckets:
  - projet-quantnuis-frontend: site Angular statique
  - quantnuis-audio-bucket: fichiers audio utilisateurs
  - quantnuis-db-bucket: backup DB Lambda
```

Le frontend envoie les appels auth/data vers EC2, et /predict vers Lambda.

## Common Commands

### Run Development Servers

```bash
# Backend (from Quantnuis-Backend/)
source venv/bin/activate
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000

# Frontend (from Quantnuis-Frontend/)
npm start  # Runs on http://localhost:4200

# Or use Docker
docker-compose up
```

### ML Pipeline

```bash
# Extract features from audio slices (~180 features per file)
python -m models.car_detector.feature_extraction
python -m models.noisy_car_detector.feature_extraction

# Optimize features (select best 40 features for better clustering)
python -m shared.feature_selection --model car_detector --top 40
python -m shared.feature_selection --model car_detector --analyze  # Analysis only

# Benchmark models (compare 10 ML models, detect overfitting)
python -m scripts.benchmark --model car_detector              # All 180 features
python -m scripts.benchmark --model car_detector --optimized  # Optimized 40 features

# Train models (generates model.h5, scaler.pkl, features.txt)
python -m models.car_detector.train
python -m models.noisy_car_detector.train

# Run inference on a single file
python -m pipeline.orchestrator audio.wav
```

### Data Management

```bash
# Add audio slices to a model's dataset
python -m data_management.slice_manager -m car -a add -s /path/to/audios
python -m data_management.slice_manager -m noisy_car -a add -s /path/to/audios

# Check dataset status
python -m data_management.slice_manager -m car -a status

# Slice long audio file using annotation CSV
python -m data_management.slicing -m car audio_long.wav annotations.csv
```

## Architecture

```
Audio File → Extract 40 optimized features (from 180: MFCC, spectral, vehicle-specific)
           → Model 1: CarDetector (prob ≥ 0.5?)
             ├─ No  → "No car detected"
             └─ Yes → Model 2: NoisyCarDetector (prob ≥ 0.5?)
                      ├─ No  → "Normal vehicle"
                      └─ Yes → "Noisy vehicle (~95dB)"
```

### Key Directories

- `api/main.py` - FastAPI endpoints + Mangum handler for Lambda
- `config/settings.py` - All configuration (paths, thresholds, secrets)
- `pipeline/orchestrator.py` - Chains both models for inference
- `shared/audio_utils.py` - Feature extraction (~180 features: MFCC, spectral, vehicle-specific)
- `shared/feature_selection.py` - Feature optimization (correlation analysis, redundancy removal)
- `scripts/benchmark.py` - Model comparison (10 models, overfitting detection, clustering analysis)
- `models/base_model.py` - Abstract base class for ML models
- `models/*/artifacts/` - Saved model files (model.h5, scaler.pkl, features.txt)
- `database/models.py` - SQLAlchemy ORM (User, CarDetection, NoisyCarAnalysis)
- `data/*/slices/` - Audio training data
- `data/*/annotation.csv` - Labels (nfile, length, label, reliability)
- `data/*/features_all.csv` - All extracted features (~180 features)
- `data/*/features_optimized.csv` - Optimized features (40 best, for training)
- `data/*/optimized_features.txt` - List of selected feature names
- `benchmark_results/` - Model comparison charts, cluster visualizations

### Database Schema

- **users**: id, email, hashed_password, is_active, is_admin, created_at
- **car_detections**: id, filename, car_detected, confidence, probability, timestamp, user_id
- **noisy_car_analyses**: id, is_noisy, confidence, probability, estimated_db, car_detection_id, user_id
- **annotation_requests**: id, filename, audio_path, annotations_data, model_type, status, annotation_count, total_duration, user_id, reviewed_by_id, created_at, reviewed_at, admin_note

## API Endpoints

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/health` | GET | No | Health check |
| `/predict` | POST | Optional | Analyze audio (simple response) |
| `/predict/detailed` | POST | Optional | Analyze audio (full response) |
| `/register` | POST | No | Register user |
| `/token` | POST | No | Login (OAuth2 form, returns JWT) |
| `/users/me` | GET | Yes | Current user info |
| `/stats` | GET | Yes | User statistics |
| `/history` | GET | Yes | Analysis history |
| `/annotation-requests` | POST | Yes | Submit annotation request |
| `/annotation-requests/my` | GET | Yes | User's annotation requests |
| `/integrate-annotations` | POST | No | Integrate annotations into dataset |
| `/admin/annotation-requests` | GET | Admin | List annotation requests |
| `/admin/annotation-requests/{id}` | GET | Admin | Request details |
| `/admin/annotation-requests/{id}/review` | POST | Admin | Approve/reject request |
| `/admin/annotation-requests/stats` | GET | Admin | Annotation stats |
| `/admin/users` | GET | Admin | List all users |
| `/admin/users/{id}/make-admin` | POST | Admin | Promote user to admin |
| `/s3-audio/files` | GET | Yes | List S3 audio files |
| `/s3-audio/presigned-url` | GET | Yes | Get presigned download URL |
| `/s3-audio/file-exists` | GET | Yes | Check if file exists in S3 |

Swagger docs: http://localhost:8000/docs

## Configuration

All config via `config/settings.py`. Key settings:

- `SAMPLE_RATE`: 22050 Hz
- `N_MFCC`: 40 coefficients
- `TOP_FEATURES_COUNT`: 12 features selected for models
- `CAR_DETECTION_THRESHOLD` / `NOISY_THRESHOLD`: 0.5
- `DATABASE_URL`: SQLite path (auto-adjusts for Lambda)
- `SECRET_KEY`: JWT secret (must change in production)

Environment variables: `DEBUG`, `SECRET_KEY`, `DB_BUCKET_NAME`, `DATABASE_PATH`, `ACCESS_TOKEN_EXPIRE_MINUTES`

## Important Constraints

- **Python 3.11 required** - TensorFlow 2.15 incompatible with Python 3.12
- **NumPy < 2.0** - Required for TensorFlow 2.15 compatibility
- Model 2 (NoisyCarDetector) only makes sense on audio containing a vehicle
- Lambda deployment requires 1024MB+ memory and 60s timeout
- Database in Lambda uses S3 for persistence (s3_manager.py)
