from __future__ import annotations

import os
import logging
from typing import Optional

from app.core.config import settings

logger = logging.getLogger(__name__)


def init_sentry() -> None:
    """Initialize Sentry if available and configured. Optional dependency."""
    dsn = os.environ.get("SENTRY_DSN") or settings.__dict__.get("SENTRY_DSN")
    if not dsn:
        logger.debug("Sentry DSN not configured; skipping Sentry init")
        return

    try:
        import sentry_sdk
        from sentry_sdk.integrations.logging import LoggingIntegration
    except Exception:
        logger.warning("sentry-sdk not installed; skipping Sentry initialization")
        return

    sentry_logging = LoggingIntegration(level=logging.INFO, event_level=logging.ERROR)
    sentry_sdk.init(dsn=dsn, integrations=[sentry_logging], traces_sample_rate=0.1)
    logger.info("Sentry initialized")


def init_opentelemetry() -> Optional[object]:
    """Initialize OpenTelemetry TracerProvider if OTLP endpoint configured and libs available.

    Returns the provider or None if not configured/available.
    """
    otlp_endpoint = os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT")
    if not otlp_endpoint:
        logger.debug("OTLP endpoint not configured; skipping OpenTelemetry init")
        return None

    try:
        from opentelemetry import trace
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
    except Exception:
        logger.warning("OpenTelemetry packages not installed; skipping OTel init")
        return None

    resource = Resource.create({"service.name": settings.APP_NAME})
    provider = TracerProvider(resource=resource)
    exporter = OTLPSpanExporter(endpoint=otlp_endpoint, insecure=True if os.environ.get("OTEL_INSECURE") else False)
    span_processor = BatchSpanProcessor(exporter)
    provider.add_span_processor(span_processor)
    trace.set_tracer_provider(provider)
    logger.info("OpenTelemetry TracerProvider configured")
    return provider
