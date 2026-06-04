"""User service — thin async wrapper around the MongoDB users collection."""
from __future__ import annotations

import logging
from typing import Optional

from pymongo.errors import DuplicateKeyError

from app.db.mongo import get_db
from app.services.auth_service import hash_password

logger = logging.getLogger(__name__)


class UserAlreadyExistsError(ValueError):
    """Raised when attempting to register an email that is already taken."""


async def get_user_by_email(email: str) -> Optional[dict]:
    """
    Return the user document for *email*, or None if not found.
    Strips _id and hashed_password before returning.
    Raises RuntimeError (from get_db) if the DB is not initialised.
    """
    db = get_db()  # raises RuntimeError if not connected — intentional
    user = await db.users.find_one({"email": email.strip().lower()})
    if user is None:
        return None
    # Never leak internal fields to callers
    user.pop("_id", None)
    user.pop("hashed_password", None)
    return user


async def create_user(
    email: str,
    password: str,
    full_name: Optional[str] = None,
) -> dict:
    """
    Hash *password* and persist a new user document.

    Returns the sanitised user dict (no _id or hashed_password).
    Raises:
        UserAlreadyExistsError: if the email is already registered.
        RuntimeError:           if the DB is not initialised.
    """
    db = get_db()

    normalised_email = email.strip().lower()
    doc = {
        "email": normalised_email,
        "full_name": full_name,
        "hashed_password": hash_password(password),
    }

    try:
        result = await db.users.insert_one(doc)
    except DuplicateKeyError:
        logger.warning("Registration attempted for existing email: %s", normalised_email)
        raise UserAlreadyExistsError(f"Email already registered: {normalised_email}")

    # Return a clean response — never expose _id or hashed_password
    return {"id": str(result.inserted_id), "email": normalised_email, "full_name": full_name}