from __future__ import annotations

import os

from celery import Celery
import redis
import os
import logging
from celery import Task

logger = logging.getLogger(__name__)


CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")
CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/0")


def _broker_url() -> str:
    return CELERY_BROKER_URL


def _result_backend() -> str:
    return CELERY_RESULT_BACKEND


celery_app = Celery(
    "talentlens_ai",
    broker=_broker_url(),
    backend=_result_backend(),
    include=["app.services.background_tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    result_backend_max_retries=3,
)


# --- Task base with retry/backoff and dead-letter support ---
class BaseTaskWithDLQ(Task):
    autoretry_for = (Exception,)
    max_retries = int(os.environ.get("CELERY_TASK_MAX_RETRIES", 5))
    default_retry_delay = int(os.environ.get("CELERY_TASK_RETRY_DELAY", 5))
    retry_backoff = True

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        # push to a Redis-based dead-letter list for later inspection
        try:
            r = redis.from_url(os.environ.get("CELERY_RESULT_BACKEND", _result_backend()))
            dlq_key = os.environ.get("CELERY_DLQ_KEY", "celery:dlq")
            payload = {
                "task": self.name,
                "task_id": task_id,
                "args": args,
                "kwargs": kwargs,
                "error": str(exc),
            }
            r.rpush(dlq_key, str(payload))
        except Exception as e:
            logger.exception("Failed to push to DLQ: %s", e)
        super().on_failure(exc, task_id, args, kwargs, einfo)


celery_app.Task = BaseTaskWithDLQ


# Optional: instrument Celery with OpenTelemetry when available
try:
    from opentelemetry.instrumentation.celery import CeleryInstrumentor

    CeleryInstrumentor().instrument()
except Exception:
    # optional dependency — skip if not installed
    pass
