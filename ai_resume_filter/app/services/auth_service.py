"""Authentication helpers: password hashing (Argon2) and JWT generation."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

from jose import jwt, JWTError
from passlib.context import CryptContext

from app.core.config import settings

# Ensure SECRET_KEY is present; settings.validate() runs at import time in config
_SECRET_KEY = settings.SECRET_KEY

_ALGORITHM = "HS256"
_DEFAULT_EXPIRE_MINUTES = settings.ACCESS_TOKEN_EXPIRE_MINUTES
_DEFAULT_REFRESH_DAYS = settings.REFRESH_TOKEN_EXPIRE_DAYS

# ── Password hashing ─────────────────────────────────────────────────────────
pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


# ── JWT ───────────────────────────────────────────────────────────────────────
def create_access_token(
    subject: str,                            # always the user's email / user-id
    expires_delta: Optional[timedelta] = None,
    extra_claims: Optional[Dict[str, Any]] = None,
) -> str:
    """
    Create a signed JWT.

    Args:
        subject:       The `sub` claim — typically the user's email.
        expires_delta: Token lifetime. Defaults to 60 minutes.
        extra_claims:  Any additional claims to embed (e.g. roles, scopes).
    """
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=_DEFAULT_EXPIRE_MINUTES)
    )
    payload: Dict[str, Any] = {
        **(extra_claims or {}),
        "sub": subject,   # set last so extra_claims can't accidentally overwrite sub
        "exp": expire,
        "iat": datetime.now(timezone.utc),  # issued-at for debugging / auditing
    }
    return jwt.encode(payload, _SECRET_KEY, algorithm=_ALGORITHM)


def create_refresh_token(subject: str, expires_delta: Optional[timedelta] = None) -> str:
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(days=_DEFAULT_REFRESH_DAYS)
    )
    payload = {"sub": subject, "exp": expire, "iat": datetime.now(timezone.utc)}
    return jwt.encode(payload, _SECRET_KEY, algorithm=_ALGORITHM)


def decode_token(token: str) -> Dict[str, Any]:
    try:
        payload = jwt.decode(token, _SECRET_KEY, algorithms=[_ALGORITHM])
        return payload
    except JWTError as exc:
        raise