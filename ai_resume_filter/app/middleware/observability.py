from __future__ import annotations

import time
import uuid
from typing import Callable

from prometheus_client import Counter, Histogram
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.logging_config import request_id_ctx_var

# Prometheus metrics
REQUEST_COUNT = Counter("http_requests_total", "Total HTTP requests", ["method", "path", "status"])
REQUEST_LATENCY = Histogram("http_request_latency_seconds", "HTTP request latency seconds", ["method", "path"])


class RequestIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # set request id
        rid = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        request_id_ctx_var.set(rid)
        response = await call_next(request)
        response.headers.setdefault("X-Request-ID", rid)
        return response


class MetricsMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        start = time.time()
        response = await call_next(request)
        elapsed = time.time() - start
        method = request.method
        path = request.url.path
        status = str(response.status_code)
        REQUEST_COUNT.labels(method=method, path=path, status=status).inc()
        REQUEST_LATENCY.labels(method=method, path=path).observe(elapsed)
        return response
