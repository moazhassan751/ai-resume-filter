from __future__ import annotations

import os
import time
import logging

try:
    import redis
except Exception:
    redis = None

from typing import Optional

logger = logging.getLogger(__name__)

DLQ_KEY = os.environ.get("CELERY_DLQ_KEY", "celery:dlq")
REDIS_URL = os.environ.get("REDIS_URL") or os.environ.get("CELERY_RESULT_BACKEND") or "redis://localhost:6379/1"


def process_message(msg: str) -> None:
    # Simple processing: log, and (optionally) push to a monitoring DB or external alerting.
    logger.error("DLQ message: %s", msg)


def run_once(r: "redis.Redis", limit: int = 100) -> int:
    popped = 0
    for _ in range(limit):
        item = r.lpop(DLQ_KEY)
        if not item:
            break
        try:
            process_message(item.decode() if isinstance(item, (bytes, bytearray)) else str(item))
        except Exception as e:
            logger.exception("Failed processing DLQ item: %s", e)
        popped += 1
    return popped


def main(poll_interval: int = 5) -> None:
    if not redis:
        logger.error("redis library not installed; DLQ consumer cannot run")
        return

    r = redis.from_url(REDIS_URL)
    logger.info("Starting DLQ consumer for key %s", DLQ_KEY)
    try:
        while True:
            count = run_once(r, limit=50)
            if count == 0:
                time.sleep(poll_interval)
    except KeyboardInterrupt:
        logger.info("DLQ consumer stopped by user")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
