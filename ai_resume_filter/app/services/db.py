"""Async MongoDB connection management (Motor)."""
from __future__ import annotations

import logging

import motor.motor_asyncio
from pymongo.errors import OperationFailure

from app.core.config import settings

logger = logging.getLogger(__name__)

_client: motor.motor_asyncio.AsyncIOMotorClient | None = None
_db: motor.motor_asyncio.AsyncIOMotorDatabase | None = None


async def connect() -> motor.motor_asyncio.AsyncIOMotorDatabase:
    """Open the Motor connection, verify it, and ensure indexes exist."""
    global _client, _db

    _client = motor.motor_asyncio.AsyncIOMotorClient(settings.MONGODB_URL)

    # Eagerly verify the connection — Motor is lazy, this pings the server
    await _client.admin.command("ping")
    logger.info("MongoDB connection established: %s", settings.MONGODB_DB)

    _db = _client[settings.MONGODB_DB]
    await _ensure_indexes(_db)
    return _db


async def _ensure_indexes(
    db: motor.motor_asyncio.AsyncIOMotorDatabase,
) -> None:
    """Create required indexes. Logs failures instead of silently ignoring them."""
    indexes = [
        ("users", [("email", 1)], {"unique": True}),
        ("metrics", [("created_at", -1)], {}),
    ]
    for collection, keys, kwargs in indexes:
        try:
            await db[collection].create_index(keys, **kwargs)
            logger.debug("Index ensured on %s: %s", collection, keys)
        except OperationFailure as exc:
            # OperationFailure covers conflicting index definitions — log, don't swallow
            logger.error(
                "Failed to create index on %s %s: %s", collection, keys, exc
            )
            raise  # re-raise so startup fails visibly on misconfiguration


def get_db() -> motor.motor_asyncio.AsyncIOMotorDatabase:
    """Return the active database handle. Raises if called before connect()."""
    if _db is None:
        raise RuntimeError("Database not initialised — call connect() first")
    return _db


async def close() -> None:
    """Close the Motor client gracefully."""
    global _client
    if _client:
        _client.close()
        _client = None
        logger.info("MongoDB connection closed")