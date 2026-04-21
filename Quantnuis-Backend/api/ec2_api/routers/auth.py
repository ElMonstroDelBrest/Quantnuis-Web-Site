#!/usr/bin/env python3
"""
================================================================================
                    EC2 API - AUTH ROUTER
================================================================================

Authentication endpoints: /register, /token, /users/me

================================================================================
"""

from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy.orm import Session

from config import get_settings
from database import get_db, User
from database.schemas import UserCreate, User as UserSchema, Token
from ..dependencies import (
    verify_password, get_password_hash, create_access_token, get_current_user
)

router = APIRouter(tags=["authentication"])
settings = get_settings()
limiter = Limiter(key_func=get_remote_address)


@router.post("/register", response_model=UserSchema)
@limiter.limit("5/minute")
def register(request: Request, user: UserCreate, db: Session = Depends(get_db)):
    """Register a new user."""
    # Check if email already exists
    db_user = db.query(User).filter(User.email == user.email).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Email deja enregistre")

    # Create the user
    hashed_password = get_password_hash(user.password)
    new_user = User(email=user.email, hashed_password=hashed_password)

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return new_user


@router.post("/token", response_model=Token)
@limiter.limit("10/minute")
async def login(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """Authenticate and get a JWT token."""
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


@router.get("/users/me", response_model=UserSchema)
async def get_me(current_user: User = Depends(get_current_user)):
    """Get the current user's information."""
    return current_user
