from __future__ import annotations

import os
import asyncio
import logging
from typing import Optional

from prometheus_client import Gauge

logger = logging.getLogger(__name__)

# Prometheus metric for DLQ size
DLQ_GAUGE = Gauge("celery_dlq_size", "Number of messages in Celery DLQ")

REDIS_URL = os.environ.get("REDIS_URL") or os.environ.get("CELERY_RESULT_BACKEND") or "redis://localhost:6379/1"
DLQ_KEY = os.environ.get("CELERY_DLQ_KEY", "celery:dlq")


async def start_dlq_monitor(poll_interval: int = 10) -> None:
    """Periodically poll Redis for DLQ length and update Prometheus gauge.

    This function is resilient: if `redis` is not installed or Redis is unreachable, it logs
    and keeps retrying without blocking the event loop.
    """
    try:
        import redis
    except Exception:
        logger.debug("redis library not installed; DLQ monitor disabled")
        return

    # Use a sync Redis client but run blocking calls in a thread via asyncio.to_thread
    try:
        r = redis.from_url(REDIS_URL)
    except Exception as exc:
        logger.warning("Unable to create Redis client for DLQ monitor: %s", exc)
        r = None

    while True:
        try:
            if r is None:
                try:
                    r = redis.from_url(REDIS_URL)
                except Exception:
                    r = None
            if r:
                length = await asyncio.to_thread(r.llen, DLQ_KEY)
                DLQ_GAUGE.set(length or 0)
            else:
                # set to 0 when unknown to avoid stale alerts
                DLQ_GAUGE.set(0)
        except Exception as exc:  # keep the loop alive on errors
            logger.debug("DLQ monitor polling error: %s", exc)
        await asyncio.sleep(poll_interval)
