from __future__ import annotations

import logging
from typing import Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger(__name__)


class OpenTelemetryMiddleware(BaseHTTPMiddleware):
    """Lightweight OpenTelemetry request span wrapper.

    This middleware requires `opentelemetry-api`/`opentelemetry-sdk` to be installed.
    It is intentionally optional; when OTel packages are absent it will be a no-op.
    """

    def __init__(self, app, service_name: str | None = None):
        super().__init__(app)
        self._enabled = False
        try:
            from opentelemetry import trace

            self._tracer = trace.get_tracer(service_name or "app")
            self._enabled = True
        except Exception:
            logger.debug("OpenTelemetry not available; middleware disabled")
            self._enabled = False

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        if not self._enabled:
            return await call_next(request)

        # Create a span for the incoming request
        with self._tracer.start_as_current_span(f"HTTP {request.method} {request.url.path}"):
            response = await call_next(request)
        return response
