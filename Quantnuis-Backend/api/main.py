#!/usr/bin/env python3
"""
================================================================================
                    API FASTAPI - POINT D'ENTRÉE PRINCIPAL
================================================================================

API REST pour l'analyse audio avec le pipeline à deux modèles.
Compatible avec le déploiement local et AWS Lambda.

Endpoints :
    - POST /predict      : Analyse un fichier audio (pipeline complet)
    - POST /register     : Inscription utilisateur
    - POST /token        : Authentification (JWT)
    - GET  /users/me     : Informations utilisateur
    - GET  /stats        : Statistiques utilisateur
    - GET  /history      : Historique des analyses
    - GET  /health       : Vérification santé de l'API

Usage local :
    uvicorn api.main:app --reload --host 0.0.0.0 --port 8000

AWS Lambda :
    Le handler Mangum est exporté automatiquement.

================================================================================
"""

import os

# Configuration des caches pour AWS Lambda (doit être fait AVANT les imports)
os.environ['NUMBA_CACHE_DIR'] = '/tmp'
os.environ['MPLCONFIGDIR'] = '/tmp'
os.environ['TRANSFORMERS_CACHE'] = '/tmp'
os.environ['XDG_CACHE_HOME'] = '/tmp'

import shutil
import tempfile
from pathlib import Path
from typing import List

from fastapi import (
    FastAPI, UploadFile, File, HTTPException, 
    Depends, status, Request
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from passlib.context import CryptContext
from jose import JWTError, jwt
from datetime import datetime, timedelta
from mangum import Mangum

from config import get_settings
from database import (
    SessionLocal, get_db, engine,
    User, CarDetection, NoisyCarAnalysis,
    S3DatabaseManager
)
from database.models import create_all_tables
from database.schemas import (
    UserCreate, User as UserSchema,
    Token, TokenData,
    UserStats, PipelineResult, PipelineResultSimplified,
    HistoryEntry
)
from pipeline import Pipeline


# ==============================================================================
# CONFIGURATION
# ==============================================================================

settings = get_settings()

# Initialisation S3 pour Lambda
s3_manager = S3DatabaseManager()
if settings.IS_LAMBDA:
    s3_manager.download()

# Création des tables
create_all_tables(engine)


# ==============================================================================
# APPLICATION FASTAPI
# ==============================================================================

app = FastAPI(
    title="Quantnuis API",
    description="API d'analyse audio pour la détection de véhicules bruyants",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Handler pour AWS Lambda
handler = Mangum(app, lifespan="off")


# ==============================================================================
# MIDDLEWARE CORS
# ==============================================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # À restreindre en production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ==============================================================================
# CONFIGURATION SÉCURITÉ
# ==============================================================================

pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


# ==============================================================================
# UTILITAIRES AUTH
# ==============================================================================

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Vérifie un mot de passe contre son hash."""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Hash un mot de passe."""
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    """Crée un token JWT."""
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=15))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


async def get_current_user(
    token: str = Depends(oauth2_scheme), 
    db: Session = Depends(get_db)
) -> User:
    """Récupère l'utilisateur actuel à partir du token."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Identifiants invalides",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    user = db.query(User).filter(User.email == email).first()
    if user is None:
        raise credentials_exception
    
    return user


def get_optional_user(
    request: Request,
    db: Session = Depends(get_db)
) -> User | None:
    """Récupère l'utilisateur si authentifié, None sinon."""
    auth_header = request.headers.get('Authorization')
    
    if not auth_header or not auth_header.startswith("Bearer "):
        return None
    
    token = auth_header.split(" ")[1]
    
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        email: str = payload.get("sub")
        if email:
            return db.query(User).filter(User.email == email).first()
    except:
        pass
    
    return None


# ==============================================================================
# INITIALISATION DU PIPELINE
# ==============================================================================

# Le pipeline est initialisé globalement pour éviter de recharger les modèles
# à chaque requête (important pour Lambda)
pipeline = Pipeline()


# ==============================================================================
# ENDPOINTS - SANTÉ
# ==============================================================================

@app.get("/health")
async def health_check():
    """Vérifie que l'API fonctionne."""
    return {
        "status": "ok",
        "version": "2.0.0",
        "environment": "lambda" if settings.IS_LAMBDA else "local",
        "models": {
            "car_detector": pipeline.car_detector.is_loaded,
            "noisy_car_detector": pipeline.noisy_car_detector.is_loaded
        }
    }


# ==============================================================================
# ENDPOINTS - AUTHENTIFICATION
# ==============================================================================

@app.post("/register", response_model=UserSchema)
def register(user: UserCreate, db: Session = Depends(get_db)):
    """Inscription d'un nouvel utilisateur."""
    # Vérifier si l'email existe déjà
    db_user = db.query(User).filter(User.email == user.email).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Email déjà enregistré")
    
    # Créer l'utilisateur
    hashed_password = get_password_hash(user.password)
    new_user = User(email=user.email, hashed_password=hashed_password)
    
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    # Synchroniser avec S3 si Lambda
    if settings.IS_LAMBDA:
        s3_manager.upload()
    
    return new_user


@app.post("/token", response_model=Token)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(), 
    db: Session = Depends(get_db)
):
    """Authentification et récupération du token JWT."""
    user = db.query(User).filter(User.email == form_data.username).first()
    
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email ou mot de passe incorrect",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token = create_access_token(
        data={"sub": user.email},
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    
    return {"access_token": access_token, "token_type": "bearer"}


@app.get("/users/me", response_model=UserSchema)
async def get_me(current_user: User = Depends(get_current_user)):
    """Récupère les informations de l'utilisateur connecté."""
    return current_user


# ==============================================================================
# ENDPOINTS - ANALYSE
# ==============================================================================

@app.post("/predict")
async def predict_audio(
    request: Request,
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """
    Analyse un fichier audio avec le pipeline complet.
    
    Le pipeline :
    1. Détecte si une voiture est présente
    2. Si oui, analyse si elle est bruyante
    
    Paramètres:
        file: Fichier audio (wav, mp3, etc.)
    
    Retourne:
        Format simplifié pour compatibilité avec le frontend :
        - hasNoisyVehicle: bool
        - confidence: float (0-1)
        - maxDecibels: int
        - message: str
    """
    # Récupérer l'utilisateur si authentifié
    user = get_optional_user(request, db)
    
    # Valider le type de fichier
    if not file.content_type or not file.content_type.startswith("audio/"):
        raise HTTPException(
            status_code=400, 
            detail="Le fichier doit être un fichier audio"
        )
    
    # Sauvegarder le fichier temporairement
    suffix = Path(file.filename).suffix if file.filename else ".wav"
    
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix, dir='/tmp') as temp_file:
        try:
            shutil.copyfileobj(file.file, temp_file)
            temp_path = temp_file.name
        finally:
            file.file.close()
    
    try:
        # Exécuter le pipeline
        result = pipeline.analyze(temp_path, verbose=False)
        
        # Enregistrer dans la BDD si utilisateur authentifié
        if user:
            # Créer l'entrée CarDetection
            car_detection = CarDetection(
                filename=file.filename or "unknown",
                car_detected=result.car_detected,
                confidence=result.car_confidence,
                probability=result.car_probability,
                user_id=user.id
            )
            db.add(car_detection)
            db.flush()  # Pour obtenir l'ID
            
            # Si voiture détectée, créer NoisyCarAnalysis
            if result.car_detected and result.is_noisy is not None:
                noisy_analysis = NoisyCarAnalysis(
                    is_noisy=result.is_noisy,
                    confidence=result.noisy_confidence or 0,
                    probability=result.noisy_probability or 0,
                    estimated_db=result.estimated_db,
                    car_detection_id=car_detection.id,
                    user_id=user.id
                )
                db.add(noisy_analysis)
            
            db.commit()
            
            # Synchroniser avec S3 si Lambda
            if settings.IS_LAMBDA:
                s3_manager.upload()
        
        # Retourner le format simplifié
        return result.to_simplified()
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
    finally:
        # Nettoyer le fichier temporaire
        if os.path.exists(temp_path):
            os.unlink(temp_path)


@app.post("/predict/detailed")
async def predict_audio_detailed(
    request: Request,
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """
    Analyse un fichier audio et retourne les résultats détaillés.
    
    Retourne les résultats complets des deux modèles.
    """
    user = get_optional_user(request, db)
    
    if not file.content_type or not file.content_type.startswith("audio/"):
        raise HTTPException(status_code=400, detail="Le fichier doit être audio")
    
    suffix = Path(file.filename).suffix if file.filename else ".wav"
    
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix, dir='/tmp') as temp_file:
        shutil.copyfileobj(file.file, temp_file)
        temp_path = temp_file.name
    
    try:
        result = pipeline.analyze(temp_path, verbose=False)
        
        # Enregistrer si authentifié (même logique que /predict)
        if user:
            car_detection = CarDetection(
                filename=file.filename or "unknown",
                car_detected=result.car_detected,
                confidence=result.car_confidence,
                probability=result.car_probability,
                user_id=user.id
            )
            db.add(car_detection)
            db.flush()
            
            if result.car_detected and result.is_noisy is not None:
                noisy_analysis = NoisyCarAnalysis(
                    is_noisy=result.is_noisy,
                    confidence=result.noisy_confidence or 0,
                    probability=result.noisy_probability or 0,
                    estimated_db=result.estimated_db,
                    car_detection_id=car_detection.id,
                    user_id=user.id
                )
                db.add(noisy_analysis)
            
            db.commit()
            
            if settings.IS_LAMBDA:
                s3_manager.upload()
        
        return result.to_dict()
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
    finally:
        if os.path.exists(temp_path):
            os.unlink(temp_path)


# ==============================================================================
# ENDPOINTS - STATISTIQUES ET HISTORIQUE
# ==============================================================================

@app.get("/stats", response_model=UserStats)
async def get_stats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Récupère les statistiques de l'utilisateur."""
    # Récupérer les détections
    detections = db.query(CarDetection).filter(
        CarDetection.user_id == current_user.id
    ).all()
    
    total = len(detections)
    
    # Compter les voitures bruyantes
    noisy_count = db.query(NoisyCarAnalysis).filter(
        NoisyCarAnalysis.user_id == current_user.id,
        NoisyCarAnalysis.is_noisy == True
    ).count()
    
    # Dernière analyse
    last_detection = db.query(CarDetection).filter(
        CarDetection.user_id == current_user.id
    ).order_by(CarDetection.timestamp.desc()).first()
    
    return {
        "total_analyses": total,
        "noisy_detections": noisy_count,  # Compatibilité frontend
        "last_analysis_date": last_detection.timestamp if last_detection else None
    }


@app.get("/history", response_model=List[HistoryEntry])
async def get_history(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    limit: int = 50
):
    """Récupère l'historique des analyses de l'utilisateur."""
    detections = db.query(CarDetection).filter(
        CarDetection.user_id == current_user.id
    ).order_by(CarDetection.timestamp.desc()).limit(limit).all()
    
    history = []
    for detection in detections:
        # Déterminer si c'est bruyant (voiture détectée ET bruyante)
        is_noisy = False
        confidence = detection.confidence  # Confiance de détection voiture
        
        if detection.car_detected and detection.noisy_analysis:
            is_noisy = detection.noisy_analysis.is_noisy
            confidence = detection.noisy_analysis.confidence
        
        entry = {
            "id": detection.id,
            "filename": detection.filename,
            "timestamp": detection.timestamp,
            "is_noisy": is_noisy,
            "confidence": confidence  # Format attendu par le frontend
        }
        
        history.append(entry)
    
    return history


# ==============================================================================
# POINT D'ENTRÉE LOCAL
# ==============================================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
