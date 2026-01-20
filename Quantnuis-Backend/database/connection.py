#!/usr/bin/env python3
"""
================================================================================
                    CONNEXION BASE DE DONNÉES
================================================================================

Configuration de la connexion SQLAlchemy.
Compatible avec le développement local et AWS Lambda.

================================================================================
"""

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from config import get_settings

settings = get_settings()

# Créer le dossier parent de la BDD si nécessaire
settings.DB_PATH.parent.mkdir(parents=True, exist_ok=True)


# ==============================================================================
# CONFIGURATION ENGINE
# ==============================================================================

engine = create_engine(
    settings.DATABASE_URL,
    connect_args={"check_same_thread": False}  # Nécessaire pour SQLite
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


# ==============================================================================
# DÉPENDANCE FASTAPI
# ==============================================================================

def get_db():
    """
    Générateur de session de base de données pour FastAPI.
    
    Usage avec FastAPI:
        @app.get("/users")
        def get_users(db: Session = Depends(get_db)):
            return db.query(User).all()
    
    Yields:
        Session: Session SQLAlchemy
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """
    Initialise la base de données (crée les tables).
    
    À appeler au démarrage de l'application.
    """
    from . import models  # Import local pour éviter les imports circulaires
    Base.metadata.create_all(bind=engine)
