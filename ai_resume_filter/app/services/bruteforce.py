from __future__ import annotations

import os
import time
from typing import Optional

try:
    import redis as redis_lib
except Exception:  # pragma: no cover - optional dependency
    redis_lib = None

# Defaults
MAX_ATTEMPTS = int(os.environ.get("BRUTEFORCE_MAX_ATTEMPTS", 5))
WINDOW_SECONDS = int(os.environ.get("BRUTEFORCE_WINDOW_SECONDS", 15 * 60))
_DLQ_KEY = os.environ.get("CELERY_DLQ_KEY", "celery:dlq")


def _redis_client():
    url = os.environ.get("REDIS_URL") or os.environ.get("CELERY_BROKER_URL") or "redis://localhost:6379/0"
    if not redis_lib:
        return None
    try:
        return redis_lib.from_url(url)
    except Exception:
        return None


def record_failed(identifier: str) -> None:
    """Record a failed attempt for `identifier` (username or IP). Uses Redis INCR with TTL."""
    r = _redis_client()
    if r:
        key = f"bf:{identifier}"
        try:
            count = r.incr(key)
            if count == 1:
                r.expire(key, WINDOW_SECONDS)
        except Exception:
            # fallback to best-effort no-op when Redis unavailable
            return
    else:
        # Redis not available — best-effort local timestamping (not durable across processes)
        return


def is_blocked(identifier: str) -> bool:
    r = _redis_client()
    if r:
        key = f"bf:{identifier}"
        try:
            count = int(r.get(key) or 0)
            return count >= MAX_ATTEMPTS
        except Exception:
            return False
    return False


def reset(identifier: str) -> None:
    r = _redis_client()
    if r:
        try:
            r.delete(f"bf:{identifier}")
        except Exception:
            pass
