"""Shared FastAPI dependencies — JWT authentication guard."""
from __future__ import annotations

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from app.services.auth_service import decode_token
from pydantic import BaseModel

from app.core.config import settings
from app.services.user_service import get_user_by_email

_SECRET_KEY = settings.SECRET_KEY

_ALGORITHM = "HS256"

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/token")


class AuthenticatedUser(BaseModel):
    email: str
    full_name: str | None = None


async def get_current_user(
    token: str = Depends(oauth2_scheme),
) -> AuthenticatedUser:
    """Decode a JWT bearer token and return the authenticated user."""
    credentials_exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = decode_token(token)
        sub: str | None = payload.get("sub")
        exp = payload.get("exp")
        if sub is None or exp is None:
            raise credentials_exc
    except JWTError:
        raise credentials_exc

    user = await get_user_by_email(sub)
    if not user:
        raise credentials_exc

    return AuthenticatedUser(email=sub, full_name=user.get("full_name"))