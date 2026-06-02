from __future__ import annotations

import time
import os
from typing import Callable, Dict

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.core.config import settings

try:
    import redis as redis_lib
except Exception:  # pragma: no cover - optional dependency
    redis_lib = None


class SecureHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response = await call_next(request)
        # Basic secure headers
        response.headers.setdefault("Strict-Transport-Security", "max-age=63072000; includeSubDomains; preload")
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "no-referrer")
        response.headers.setdefault("Permissions-Policy", "geolocation=()")
        return response


class SimpleRateLimitMiddleware(BaseHTTPMiddleware):
    """Redis-backed rate limiter with an in-memory fallback.

    Uses fixed window counters stored in Redis keyed by client IP and window index.
    """

    def __init__(self, app, max_requests: int = 100, window_seconds: int = 60):
        super().__init__(app)
        self.max_requests = max_requests
        self.window = window_seconds
        self._clients: Dict[str, list[float]] = {}
        self._redis = None
        self._redis_url = os.environ.get("REDIS_URL") or os.environ.get("CELERY_BROKER_URL") or "redis://localhost:6379/0"
        if redis_lib:
            try:
                self._redis = redis_lib.from_url(self._redis_url)
            except Exception:
                self._redis = None

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        client = request.client.host if request.client else "unknown"
        now = int(time.time())
        window_index = now // self.window

        if self._redis:
            key = f"rl:{client}:{window_index}"
            try:
                count = self._redis.incr(key)
                if count == 1:
                    self._redis.expire(key, self.window)
                if count > self.max_requests:
                    return Response(status_code=429, content="Too Many Requests")
            except Exception:
                # Redis glitch — fall back to in-memory
                pass

        # Fallback in-memory sliding window
        window_start = time.time() - self.window
        timestamps = self._clients.get(client, [])
        timestamps = [t for t in timestamps if t > window_start]
        timestamps.append(time.time())
        self._clients[client] = timestamps
        if len(timestamps) > self.max_requests:
            return Response(status_code=429, content="Too Many Requests")

        return await call_next(request)
