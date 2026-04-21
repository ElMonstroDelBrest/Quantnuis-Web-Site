# api/lambda_api/

API stateless deployee sur AWS Lambda. Effectue la prediction IA
(pipeline cascade CarDetector -> NoisyCarDetector). Pas de BDD.

## Structure

```
lambda_api/
├── main.py              # Entry point FastAPI + Mangum handler
└── routers/
    └── predict.py       # /predict, /predict/detailed
```

## Demarrage local

```bash
uvicorn api.lambda_api.main:app --reload --host 0.0.0.0 --port 8001
```

## Deploy Lambda

Le handler Mangum est exporte dans `main.py` :
```python
from api.lambda_api.main import handler  # pour CMD dans Dockerfile.lambda
```

## main.py

- Initialise le Pipeline globalement (evite de recharger les modeles a chaque requete)
- `get_pipeline()` : singleton du pipeline
- Pre-charge les modeles au startup

## Endpoints

### Predict (`routers/predict.py`)

| Endpoint | Methode | Auth | Parametres | Description |
|---|---|---|---|---|
| `/predict` | POST | Optionnel | multipart: `file` (audio) | Analyse audio, retourne format simplifie |
| `/predict/detailed` | POST | Optionnel | multipart: `file` (audio) | Analyse audio, retourne format complet |
| `/health` | GET | Non | - | Statut API + modeles charges |

### Format `/predict` (simplifie)

```json
{
  "hasNoisyVehicle": true,
  "carDetected": true,
  "confidence": 0.95,
  "message": "VOITURE BRUYANTE detectee !",
  "filename": "audio.wav",
  "_full_result": { ... }
}
```

### Format `/predict/detailed`

```json
{
  "car_detected": true,
  "car_confidence": 92.5,
  "car_probability": 0.925,
  "is_noisy": true,
  "noisy_confidence": 99.4,
  "noisy_probability": 0.994,
  "estimated_db": 95,
  "message": "VOITURE BRUYANTE detectee !",
  "filename": "audio.wav"
}
```

### Extensions audio supportees

`.wav`, `.mp3`, `.ogg`, `.flac`, `.m4a`
