from __future__ import annotations

import logging
import sys
from contextvars import ContextVar
from pythonjsonlogger.json import JsonFormatter

# Context var used to store request id for the current request
request_id_ctx_var: ContextVar[str | None] = ContextVar("request_id", default=None)


class RequestIdFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        rid = request_id_ctx_var.get(None)
        record.request_id = rid
        return True


def configure_logging(level: int = logging.INFO) -> None:
    """Configure structured JSON logging for the application."""
    handler = logging.StreamHandler(sys.stdout)
    fmt = JsonFormatter(
        fmt="%(asctime)s %(levelname)s %(name)s %(message)s %(request_id)s",
    )
    handler.setFormatter(fmt)
    root = logging.getLogger()
    root.setLevel(level)
    # clear existing handlers
    for h in list(root.handlers):
        root.removeHandler(h)
    root.addHandler(handler)
    # install request id filter globally
    root.addFilter(RequestIdFilter())
