"""Authentication utilities."""

import uuid
from datetime import datetime, timedelta
from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from pydantic import BaseModel
from src.config.settings import settings

security = HTTPBearer()


class TokenData(BaseModel):
    """Token data model."""
    user_id: uuid.UUID
    email: str
    role: str = "user"


def create_access_token(user_data: dict) -> str:
    """Create JWT access token."""
    to_encode = user_data.copy()
    expire = datetime.utcnow() + timedelta(hours=settings.jwt_expire_hours)
    to_encode.update({"exp": expire})
    
    encoded_jwt = jwt.encode(
        to_encode, 
        settings.jwt_secret_key, 
        algorithm=settings.jwt_algorithm
    )
    return encoded_jwt


def verify_token(token: str) -> TokenData:
    """Verify and decode JWT token."""
    try:
        payload = jwt.decode(
            token, 
            settings.jwt_secret_key, 
            algorithms=[settings.jwt_algorithm]
        )
        
        user_id = payload.get("user_id")
        email = payload.get("email")
        role = payload.get("role", "user")
        
        if user_id is None or email is None:
            raise JWTError("Invalid token payload")
        
        return TokenData(
            user_id=uuid.UUID(user_id),
            email=email,
            role=role
        )
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> TokenData:
    """Get current user from JWT token."""
    return verify_token(credentials.credentials)


async def get_current_user_id(current_user: TokenData = Depends(get_current_user)) -> uuid.UUID:
    """Get current user ID."""
    return current_user.user_id