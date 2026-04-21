# database/

Couche base de donnees : ORM SQLAlchemy, schemas Pydantic, gestion S3.

## Structure

```
database/
├── connection.py       # Engine SQLAlchemy, SessionLocal, get_db()
├── models.py           # Modeles ORM (User, CarDetection, NoisyCarAnalysis, AnnotationRequest)
├── schemas.py          # Schemas Pydantic pour validation API
├── s3_manager.py       # Persistance SQLite sur S3 (Lambda)
└── s3_audio_manager.py # Gestion fichiers audio sur S3 (annotation)
```

## connection.py

| Export | Type | Description |
|---|---|---|
| `engine` | Engine | Engine SQLAlchemy (SQLite, `check_same_thread=False`) |
| `SessionLocal` | sessionmaker | Factory de sessions |
| `Base` | declarative_base | Base ORM |
| `get_db()` | Generator | Dependance FastAPI : yield session, close au finally |
| `init_db()` | function | Cree toutes les tables |

## models.py - Tables ORM

### User (`users`)

| Colonne | Type | Description |
|---|---|---|
| `id` | Integer PK | Auto-increment |
| `email` | String unique | Email de connexion |
| `hashed_password` | String | Hash bcrypt |
| `is_active` | Boolean | Compte actif (defaut: True) |
| `is_admin` | Boolean | Droits admin (defaut: False) |
| `created_at` | DateTime | Date de creation |

Relations : `car_detections`, `noisy_analyses`, `annotation_requests`

### CarDetection (`car_detections`)

| Colonne | Type | Description |
|---|---|---|
| `id` | Integer PK | Auto-increment |
| `filename` | String | Nom du fichier audio |
| `car_detected` | Boolean | Voiture detectee ? |
| `confidence` | Float | Confiance 0-100 |
| `probability` | Float | Probabilite sigmoid 0-1 |
| `timestamp` | DateTime | Date de l'analyse |
| `audio_duration` | Float (nullable) | Duree en secondes |
| `user_id` | FK -> users | Utilisateur |

Relations : `owner` (User), `noisy_analysis` (1-to-1 avec NoisyCarAnalysis)

### NoisyCarAnalysis (`noisy_car_analyses`)

| Colonne | Type | Description |
|---|---|---|
| `id` | Integer PK | Auto-increment |
| `is_noisy` | Boolean | Bruyant ? |
| `confidence` | Float | Confiance 0-100 |
| `probability` | Float | Probabilite 0-1 |
| `estimated_db` | Integer (nullable) | Estimation decibels |
| `car_detection_id` | FK -> car_detections (unique) | Relation 1-to-1 |
| `user_id` | FK -> users | Utilisateur |

Cree UNIQUEMENT si une voiture a ete detectee par le modele 1.

### AnnotationRequest (`annotation_requests`)

| Colonne | Type | Description |
|---|---|---|
| `id` | Integer PK | Auto-increment |
| `filename` | String | Nom du fichier audio |
| `audio_path` | String | Chemin du fichier stocke |
| `annotations_data` | Text | JSON des annotations |
| `model_type` | String | `car_detector` ou `noisy_car_detector` |
| `status` | String | `pending`, `approved`, `rejected` |
| `annotation_count` | Integer | Nombre d'annotations |
| `total_duration` | Float | Duree totale annotee (s) |
| `user_id` | FK -> users | Soumis par |
| `reviewed_by_id` | FK -> users | Traite par (admin) |
| `created_at` / `reviewed_at` | DateTime | Dates |
| `admin_note` | Text | Note de l'admin |

## schemas.py - Schemas Pydantic

| Schema | Usage |
|---|---|
| `UserCreate` | POST /register body (`email`, `password`) |
| `User` | Response user (id, email, is_active, is_admin, created_at) |
| `Token` | POST /token response (`access_token`, `token_type`) |
| `TokenData` | Contenu interne du JWT |
| `PipelineResult` | Response /predict/detailed |
| `PipelineResultSimplified` | Response /predict (`hasNoisyVehicle`, `carDetected`, `confidence`, `message`) |
| `UserStats` | Response /stats |
| `HistoryEntry` | Item de /history |
| `AnnotationRequestCreate` | Body soumission annotation |
| `AnnotationRequestResponse` | Response annotation |
| `AnnotationRequestReview` | Body admin review (`action`, `note`) |
| `AnnotationRequestStats` | Response /admin/annotation-requests/stats |

## s3_manager.py - S3DatabaseManager

Persistance de la BDD SQLite sur S3 pour Lambda (filesystem en lecture seule sauf /tmp).

| Methode | Description |
|---|---|
| `download()` | Telecharge la BDD depuis S3 vers `/tmp/quantnuis.db` |
| `upload()` | Upload la BDD locale vers S3 |
| `sync_after_write()` | Appelle upload() si on est sur Lambda |
| `ensure_downloaded()` | Appelle download() si on est sur Lambda |

## s3_audio_manager.py - S3AudioManager

Gestion des fichiers audio pour l'interface d'annotation.

| Methode | Parametres | Description |
|---|---|---|
| `list_audio_files(prefix, max_files)` | prefix="", max_files=100 | Liste les .wav/.mp3/etc. tries par date |
| `get_presigned_url(key, expiration)` | key=chemin S3, expiration=3600s | Genere URL de telechargement temporaire |
| `file_exists(key)` | key=chemin S3 | True/False |
| `get_file_metadata(key)` | key=chemin S3 | Retourne S3AudioFile ou None |

Extensions reconnues : `.wav`, `.mp3`, `.ogg`, `.flac`, `.m4a`, `.mp4`
