#!/usr/bin/env python3
"""
================================================================================
                    EC2 API - DEPENDENCIES
================================================================================

Authentication and database dependencies for EC2 API.
Shared across all routers.

================================================================================
"""

import bcrypt
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from passlib.context import CryptContext
from jose import JWTError, jwt
from datetime import datetime, timedelta

from config import get_settings
from database import get_db, User

settings = get_settings()

# ==============================================================================
# SECURITY CONFIGURATION
# ==============================================================================

pwd_context = CryptContext(schemes=["bcrypt", "pbkdf2_sha256"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


# ==============================================================================
# PASSWORD UTILITIES
# ==============================================================================

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    try:
        return pwd_context.verify(plain_password, hashed_password)
    except Exception:
        # Direct bcrypt verification as fallback
        try:
            return bcrypt.checkpw(
                plain_password.encode('utf-8'),
                hashed_password.encode('utf-8')
            )
        except Exception:
            return False


def get_password_hash(password: str) -> str:
    """Hash a password."""
    return pwd_context.hash(password)


# ==============================================================================
# TOKEN UTILITIES
# ==============================================================================

def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    """Create a JWT token."""
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=15))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


# ==============================================================================
# USER DEPENDENCIES
# ==============================================================================

async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> User:
    """Get the current authenticated user from the token."""
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
    """Get the user if authenticated, None otherwise."""
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


async def get_admin_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """Verify that the user is an administrator."""
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acces reserve aux administrateurs"
        )
    return current_user
