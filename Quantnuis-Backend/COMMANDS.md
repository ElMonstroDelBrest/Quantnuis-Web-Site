# Quantnuis - Référence des Commandes

Guide complet de toutes les commandes disponibles dans le projet.

---

## Table des matières

1. [Serveurs de développement](#serveurs-de-développement)
2. [Pipeline ML](#pipeline-ml)
3. [Gestion des données](#gestion-des-données)
4. [Analyse et Benchmark](#analyse-et-benchmark)
5. [Déploiement](#déploiement)
6. [Base de données](#base-de-données)
7. [Docker](#docker)

---

## Serveurs de développement

### Backend (FastAPI)

```bash
# Activer l'environnement virtuel
source venv/bin/activate

# Lancer le serveur de développement (port 8000)
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000

# Lancer en production
uvicorn api.main:app --host 0.0.0.0 --port 8000 --workers 4
```

**Endpoints disponibles :**
- API Docs : http://localhost:8000/docs
- Health check : http://localhost:8000/health

### Frontend (Angular)

```bash
cd ../Quantnuis-Frontend

# Installer les dépendances
npm install

# Lancer le serveur de développement (port 4200)
npm start

# Build de production
npm run build
```

---

## Pipeline ML

### 1. Extraction de features

Extrait ~180 features audio (MFCC, spectral, véhicule-spécifiques) depuis les slices audio.

```bash
# Car Detector - Extraction complète
python -m models.car_detector.feature_extraction

# Car Detector - Forcer la réextraction
python -m models.car_detector.feature_extraction --force

# Car Detector - Voir le statut
python -m models.car_detector.feature_extraction status

# Noisy Car Detector - Extraction complète
python -m models.noisy_car_detector.feature_extraction

# Noisy Car Detector - Forcer la réextraction
python -m models.noisy_car_detector.feature_extraction --force
```

**Fichiers générés :**
- `data/car_detector/features_all.csv` (182 features)
- `data/noisy_car_detector/features_all.csv`

### 2. Optimisation des features

Sélectionne les meilleures features pour améliorer le clustering et réduire l'overfitting.

```bash
# Analyser les features (sans modifier)
python -m shared.feature_selection --model car_detector --analyze
python -m shared.feature_selection --model noisy_car_detector --analyze

# Créer le dataset optimisé (40 meilleures features)
python -m shared.feature_selection --model car_detector --top 40
python -m shared.feature_selection --model noisy_car_detector --top 40

# Personnaliser le nombre de features
python -m shared.feature_selection --model car_detector --top 50
```

**Fichiers générés :**
- `data/car_detector/features_optimized.csv` (40 features)
- `data/car_detector/optimized_features.txt` (liste des noms)

### 3. Entraînement des modèles

```bash
# Entraîner Car Detector
python -m models.car_detector.train

# Entraîner Noisy Car Detector
python -m models.noisy_car_detector.train
```

**Fichiers générés :**
- `models/*/artifacts/model.h5` - Modèle TensorFlow
- `models/*/artifacts/scaler.pkl` - StandardScaler
- `models/*/artifacts/features.txt` - Features utilisées

### 4. Inférence

```bash
# Analyser un fichier audio
python -m pipeline.orchestrator chemin/vers/audio.wav

# Exemple
python -m pipeline.orchestrator data/test_audio.wav
```

---

## Gestion des données

### Slice Manager

Gère les slices audio (ajouter, supprimer, lister).

```bash
# Voir le statut du dataset
python -m data_management.slice_manager -m car -a status
python -m data_management.slice_manager -m noisy_car -a status

# Ajouter des slices
python -m data_management.slice_manager -m car -a add -s /chemin/vers/audios/
python -m data_management.slice_manager -m noisy_car -a add -s /chemin/vers/audios/

# Lister les slices
python -m data_management.slice_manager -m car -a list

# Supprimer un slice
python -m data_management.slice_manager -m car -a remove -f slice_001.wav
```

**Options :**
- `-m` : Modèle (`car` ou `noisy_car`)
- `-a` : Action (`status`, `add`, `list`, `remove`)
- `-s` : Source (dossier contenant les audios)
- `-f` : Fichier spécifique

### Slicing

Découpe un long fichier audio en slices selon un CSV d'annotations.

```bash
# Découper un fichier audio
python -m data_management.slicing -m car audio_long.wav annotations.csv

# Format du CSV d'annotations :
# start,end,label
# 0.0,3.0,1
# 3.0,6.0,0
```

---

## Analyse et Benchmark

### Benchmark des modèles

Compare 10 modèles ML, détecte l'overfitting, analyse le clustering.

```bash
# Benchmark avec toutes les features (182)
python -m shared.benchmark --model car_detector
python -m shared.benchmark --model noisy_car_detector

# Benchmark avec features optimisées (40)
python -m shared.benchmark --model car_detector --optimized
python -m shared.benchmark --model noisy_car_detector --optimized

# Afficher les suggestions de nouvelles features
python -m shared.benchmark --model car_detector --add-features

# Spécifier un dossier de sortie
python -m shared.benchmark --model car_detector --output-dir mon_dossier
```

**Modèles comparés :**
- Logistic Regression
- Random Forest
- Gradient Boosting
- SVM (RBF & Linear)
- KNN (k=3 & k=5)
- Naive Bayes
- MLP (small & current)

**Fichiers générés dans `benchmark_results/` :**
- `clusters_car_detector.png` - Visualisation PCA/t-SNE
- `model_comparison_car_detector.png` - Comparaison F1 scores
- `learning_curves_car_detector.png` - Détection overfitting
- `problematic_slices.csv` - Slices mal classés

### Analyse des features

```bash
# Voir les top features corrélées au label
python -m shared.feature_selection --model car_detector --analyze

# Output :
# - Top 20 features par corrélation
# - Catégories de features (MFCC, Delta, Spectral, etc.)
# - Recommandations
```

---

## Déploiement

### GitHub Actions (automatique)

Le déploiement est automatique sur push vers `main` :
- **Backend** → AWS Lambda
- **Frontend** → AWS S3 + CloudFront

### Manuel

```bash
# Build du frontend
cd ../Quantnuis-Frontend
npm run build

# Sync vers S3
aws s3 sync dist/quantnuis_dashboard/browser s3://quantnuis-frontend --delete

# Invalider le cache CloudFront
aws cloudfront create-invalidation --distribution-id XXXX --paths "/*"
```

---

## Base de données

### Scripts utilitaires

```bash
# Promouvoir un utilisateur en admin
python scripts/make_admin.py email@example.com

# Migrer SQLite vers PostgreSQL
python scripts/migrate_sqlite_to_postgres.py
```

### Via l'API

```bash
# Créer un utilisateur
curl -X POST http://localhost:8000/register \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com", "password": "password123"}'

# Obtenir un token JWT
curl -X POST http://localhost:8000/token \
  -d "username=user@example.com&password=password123"

# Voir mes infos
curl http://localhost:8000/users/me \
  -H "Authorization: Bearer <token>"
```

---

## Docker

```bash
# Lancer tous les services
docker-compose up

# Lancer en arrière-plan
docker-compose up -d

# Rebuild après modifications
docker-compose up --build

# Voir les logs
docker-compose logs -f

# Arrêter
docker-compose down
```

---

## Résumé rapide

| Tâche | Commande |
|-------|----------|
| Lancer le backend | `uvicorn api.main:app --reload` |
| Lancer le frontend | `npm start` (dans Quantnuis-Frontend) |
| Extraire les features | `python -m models.car_detector.feature_extraction` |
| Optimiser les features | `python -m shared.feature_selection --model car_detector --top 40` |
| Benchmark | `python -m shared.benchmark --model car_detector --optimized` |
| Entraîner | `python -m models.car_detector.train` |
| Inférence | `python -m pipeline.orchestrator audio.wav` |
| Statut dataset | `python -m data_management.slice_manager -m car -a status` |

---

## Variables d'environnement

| Variable | Description | Défaut |
|----------|-------------|--------|
| `DEBUG` | Mode debug | `False` |
| `SECRET_KEY` | Clé JWT | (requis en prod) |
| `DATABASE_PATH` | Chemin SQLite | `database/quantnuis.db` |
| `AUDIO_BUCKET_NAME` | Bucket S3 audio | `quantnuis-audio-bucket` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Durée token JWT | `30` |

---

*Dernière mise à jour : Janvier 2026*
