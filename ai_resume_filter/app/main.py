"""
TalentLens AI — FastAPI application entry point.
Initialises services in order: DB → data service → ML model.
"""
from __future__ import annotations

import asyncio
import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware

from app.middleware.security import SecureHeadersMiddleware, SimpleRateLimitMiddleware

from app.core.config import settings
from app.logging_config import configure_logging, request_id_ctx_var
from app.observability import init_sentry, init_opentelemetry
from app.middleware.observability import RequestIdMiddleware, MetricsMiddleware
from app.middleware.otel import OpenTelemetryMiddleware
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
from fastapi.responses import PlainTextResponse, JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from app.api.v1 import api_router
from app.services import model_service
from app.services import db as db_service
from app.services.embedding_service import get_embedding_service
from app.services.vector_service import get_vector_service
from app.services.data_service import init_data_service, shutdown_data_service
from app.monitoring.dlq_metrics import start_dlq_monitor

configure_logging(level=(logging.DEBUG if settings.DEBUG else logging.INFO))
init_sentry()
init_opentelemetry()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup sequence
    try:
        await db_service.connect()
        logger.info("Connected to MongoDB")
    except Exception:
        logger.warning("MongoDB unavailable — running without persistence")

    try:
        await init_data_service()
        logger.info("Data service initialised")
    except Exception as exc:
        logger.warning("Data service init warning: %s", exc)

    try:
        model_path = os.environ.get("MODEL_PATH") or settings.MODEL_PATH
        model = model_service.load_model(model_path)
        if model is None:
            logger.warning("No model found at %s — train first", model_path)
        else:
            logger.info("ML model loaded from %s", model_path)
    except Exception as exc:
        logger.exception("Error loading model: %s", exc)

    try:
        get_embedding_service().load_model()
        get_vector_service().initialize()
        logger.info("Semantic embedding stack initialised")
    except Exception as exc:
        logger.warning("Semantic embedding stack unavailable: %s", exc)

    try:
        app.state.dlq_monitor_task = asyncio.create_task(start_dlq_monitor())
    except Exception:
        app.state.dlq_monitor_task = None
        logger.debug("DLQ monitor not started")

    yield

    # Shutdown sequence
    task = getattr(app.state, "dlq_monitor_task", None)
    if task is not None:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
        except Exception:
            pass

    try:
        await shutdown_data_service()
    except Exception:
        pass
    try:
        db_service.close()
    except Exception:
        pass

app = FastAPI(
    title="TalentLens AI",
    description="Agentic Recruitment Intelligence Platform",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Trusted host middleware — ensures Host header is within allowed set
app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.ALLOWED_HOSTS)

# Observability middleware
app.add_middleware(RequestIdMiddleware)
try:
    # Add OpenTelemetry middleware if OTel packages are present. It's safe to import lazily.
    app.add_middleware(OpenTelemetryMiddleware, service_name=settings.APP_NAME)
except Exception:
    pass
app.add_middleware(MetricsMiddleware)

# Security middlewares
app.add_middleware(SecureHeadersMiddleware)
# Simple rate limiter (in-memory). For multi-worker deployments, replace with Redis-backed limiter.
app.add_middleware(SimpleRateLimitMiddleware, max_requests=200, window_seconds=60)


# Global exception handlers
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    # ensure request id is present
    rid = request.headers.get("X-Request-ID") or request_id_ctx_var.get(None)
    logging.getLogger(__name__).exception("Unhandled exception: %s", exc)
    return JSONResponse(
        status_code=500,
        content={"error": "internal_server_error", "request_id": rid, "detail": str(exc)},
    )


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    rid = request.headers.get("X-Request-ID") or request_id_ctx_var.get(None)
    return JSONResponse(status_code=exc.status_code, content={"error": exc.detail, "request_id": rid})


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    rid = request.headers.get("X-Request-ID") or request_id_ctx_var.get(None)
    return JSONResponse(status_code=422, content={"error": "validation_error", "request_id": rid, "detail": exc.errors()})


# Prometheus metrics endpoint
@app.get("/metrics")
def metrics():
    data = generate_latest()
    return PlainTextResponse(data.decode("utf-8"), media_type=CONTENT_TYPE_LATEST)


# Liveness and readiness endpoints
@app.get("/live")
async def live():
    return {"status": "alive"}


@app.get("/ready")
async def ready():
    # Readiness: check MongoDB connectivity if configured, else return ready.
    mongo_url = settings.MONGODB_URL
    if not mongo_url:
        return {"status": "ready"}
    try:
        from motor.motor_asyncio import AsyncIOMotorClient

        client = AsyncIOMotorClient(mongo_url)
        await client.admin.command("ping")
        client.close()
    except Exception:
        return JSONResponse(status_code=503, content={"status": "not_ready"})
    return {"status": "ready"}

app.include_router(api_router, prefix="/api/v1")


@app.get("/", tags=["root"])
async def root():
    return {"message": "TalentLens AI API is running", "version": "2.0.0"}


@app.get("/health", tags=["root"])
async def health_check():
    return {"status": "healthy", "service": "talentlens-ai"}