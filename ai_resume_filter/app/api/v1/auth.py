"""Authentication routes: register and token."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordRequestForm

from app.schemas.auth import Token, UserCreate, UserOut
from app.services import user_service
from app.services.auth_service import create_access_token, verify_password, create_refresh_token
import logging

logger = logging.getLogger(__name__)
from app.services.bruteforce import record_failed, is_blocked, reset
from app.services.user_service import UserAlreadyExistsError

router = APIRouter(tags=["auth"])


@router.post("/register", response_model=UserOut, status_code=201)
async def register(body: UserCreate) -> UserOut:
    """Register a new user account."""
    try:
        created = await user_service.create_user(
            body.email, body.password, body.full_name
        )
    except UserAlreadyExistsError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))

    return UserOut(id=created.get("id"), email=created["email"], full_name=created.get("full_name"))


@router.post("/token", response_model=Token)
async def login(request: Request, form_data: OAuth2PasswordRequestForm = Depends()) -> Token:
    """Obtain a JWT bearer token using email + password."""
    # Fetch full document separately so hashed_password is available for verification
    from app.db.mongo import get_db
    db = get_db()
    raw_user = await db.users.find_one({"email": form_data.username.strip().lower()})

    client = request.client.host if request.client else form_data.username
    blocked_key = f"bf:{form_data.username}:{client}"
    if is_blocked(blocked_key):
        logger.warning("Blocked login attempt for %s from %s", form_data.username, client)
        raise HTTPException(status_code=429, detail="Too many failed attempts, try later")

    if not raw_user or not verify_password(
        form_data.password, raw_user.get("hashed_password", "")
    ):
        record_failed(blocked_key)
        logger.warning("Failed login for %s from %s", form_data.username, client)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # successful login — reset any brute-force counters for this key
    reset(blocked_key)
    access_token = create_access_token(subject=raw_user["email"])
    refresh_token = create_refresh_token(subject=raw_user["email"])
    logger.info("Successful login for %s from %s", raw_user["email"], client)
    return Token(access_token=access_token, refresh_token=refresh_token, expires_in=3600)