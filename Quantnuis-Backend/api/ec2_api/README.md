# api/ec2_api/

API stateful deployee sur EC2. Gere l'authentification, les donnees utilisateur,
les annotations et l'administration. Connectee a PostgreSQL en prod.

## Structure

```
ec2_api/
├── main.py              # Entry point FastAPI (uvicorn)
├── dependencies.py      # Auth utilities partagees entre routers
├── github_integration.py # Push annotations approuvees sur GitHub
└── routers/
    ├── auth.py          # /register, /token, /users/me
    ├── user_data.py     # /stats, /history, /analysis-results
    ├── annotations.py   # /annotation-requests, /annotation-requests/my
    ├── admin.py         # /admin/*
    └── s3_audio.py      # /s3-audio/*
```

## Demarrage

```bash
uvicorn api.ec2_api.main:app --reload --host 0.0.0.0 --port 8000
```

## dependencies.py - Utilitaires d'authentification

| Fonction | Signature | Description |
|---|---|---|
| `verify_password` | `(plain: str, hashed: str) -> bool` | Verifie un password contre son hash (passlib + fallback bcrypt) |
| `get_password_hash` | `(password: str) -> str` | Hash un mot de passe (bcrypt) |
| `create_access_token` | `(data: dict, expires_delta: timedelta) -> str` | Cree un JWT HS256 |
| `get_current_user` | `(token, db) -> User` | Dependance FastAPI : extrait le user du Bearer token |
| `get_optional_user` | `(request, db) -> User | None` | Comme get_current_user mais nullable |
| `get_admin_user` | `(current_user) -> User` | Verifie is_admin=True, 403 sinon |

## github_integration.py

| Fonction | Description |
|---|---|
| `push_approved_annotation(audio_path, annotations_data, model_type, user_email, request_id)` | Push audio + CSV + metadata.json sur GitHub via l'API Git Trees. Cree un commit sur main. |

Necessite `GITHUB_TOKEN` en variable d'environnement.

## Endpoints

### Auth (`routers/auth.py`)

| Endpoint | Methode | Auth | Description |
|---|---|---|---|
| `/register` | POST | Non | Inscription. Body: `{email, password}`. Retourne User. |
| `/token` | POST | Non | Login OAuth2 form (`username`=email). Retourne `{access_token, token_type}`. |
| `/users/me` | GET | Oui | Info de l'utilisateur connecte. |

### User Data (`routers/user_data.py`)

| Endpoint | Methode | Auth | Parametres | Description |
|---|---|---|---|---|
| `/stats` | GET | Oui | - | `{total_analyses, noisy_detections, last_analysis_date}` |
| `/history` | GET | Oui | `?limit=50` | Liste des analyses (id, filename, timestamp, is_noisy, confidence) |
| `/analysis-results` | POST | Oui | Body JSON | Stocke les resultats d'analyse venant de Lambda |

### Annotations (`routers/annotations.py`)

| Endpoint | Methode | Auth | Parametres | Description |
|---|---|---|---|---|
| `/annotation-requests` | POST | Oui | multipart: `audio` (file), `annotations` (CSV), `model` ("car"/"noisy_car") | Soumet une demande d'annotation |
| `/annotation-requests/my` | GET | Oui | - | Liste ses propres demandes |

### Admin (`routers/admin.py`)

| Endpoint | Methode | Auth | Parametres | Description |
|---|---|---|---|---|
| `/admin/annotation-requests` | GET | Admin | `?status_filter=pending` | Liste les demandes (filtrable: pending/approved/rejected/all) |
| `/admin/annotation-requests/stats` | GET | Admin | - | Stats: total_pending, total_approved, total_rejected |
| `/admin/annotation-requests/{id}` | GET | Admin | - | Details d'une demande (avec annotations JSON) |
| `/admin/annotation-requests/{id}/review` | POST | Admin | Body: `{action: "approve"/"reject", note}` | Approuve/rejette. Si approuve -> push GitHub. |
| `/admin/users` | GET | Admin | - | Liste tous les utilisateurs |
| `/admin/users/{id}/make-admin` | POST | Admin | - | Promouvoir un user en admin |

### S3 Audio (`routers/s3_audio.py`)

| Endpoint | Methode | Auth | Parametres | Description |
|---|---|---|---|---|
| `/s3-audio/files` | GET | Oui | `?prefix=&max_files=100` | Liste les fichiers audio du bucket S3 |
| `/s3-audio/presigned-url` | GET | Oui | `?key=path/file.wav&expiration=3600` | Genere URL presignee pour telecharger |
| `/s3-audio/file-exists` | GET | Oui | `?key=path/file.wav` | Verifie si un fichier existe dans S3 |
