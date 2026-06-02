"""Model routes: load, predict, metrics."""
from __future__ import annotations

import logging
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException

from app.core.celery_app import celery_app
from app.api.deps import get_current_user
from app.schemas.insights import ClassificationReportResponse, TrainingRunResponse
from app.schemas.model import Metrics, PredictRequest, PredictResponse
from app.services.background_tasks import train_baseline_task
from app.services.insights_service import build_classification_report
from app.services import model_service
from app.services.db import get_db
from celery.result import AsyncResult

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/load")
async def load_model():
    """Eagerly load the ML model into memory."""
    model = model_service.load_model()
    if model is None:
        raise HTTPException(status_code=404, detail="Model not found — run train_model.py first")
    return {"message": "model loaded", "ready": True}


@router.post("/predict", response_model=PredictResponse)
async def predict(req: PredictRequest, current_user=Depends(get_current_user)):
    """Run classification inference on the supplied feature map."""
    result = model_service.predict(req.data)
    if "error" in result:
        raise HTTPException(status_code=500, detail=result["error"])
    return result


@router.post("/train-async", response_model=TrainingRunResponse)
async def train_async(current_user=Depends(get_current_user)) -> TrainingRunResponse:
    task = train_baseline_task.delay()
    return TrainingRunResponse(task_id=task.id)


@router.get("/train-status/{task_id}")
async def train_status(task_id: str, current_user=Depends(get_current_user)):
    result = AsyncResult(task_id, app=celery_app)
    payload = {"task_id": task_id, "status": result.status}
    if result.successful():
        payload["result"] = result.result
    elif result.failed():
        payload["error"] = str(result.result)
    return payload


@router.get("/report", response_model=ClassificationReportResponse)
async def classification_report():
    report = await build_classification_report()
    return ClassificationReportResponse(**report)


@router.post("/metrics")
async def save_metrics(m: Metrics, current_user=Depends(get_current_user)):
    """Persist evaluation metrics (called after a training run)."""
    payload = m.dict()
    payload["created_at"] = datetime.utcnow()
    payload["user"] = current_user.get("email")
    try:
        db = get_db()
    except Exception:
        db = None

    if db is not None:
        await db.metrics.insert_one(payload)
        payload.pop("_id", None)
        return {"status": "saved", "metrics": payload}
    return {"status": "no-db", "metrics": payload}


@router.get("/metrics")
async def get_metrics():
    """Return the most recently saved metrics, or hardcoded fallback."""
    try:
        db = get_db()
    except Exception:
        db = None

    if db is not None:
        doc = await db.metrics.find_one(sort=[("created_at", -1)])
        if doc:
            doc.pop("_id", None)
            # Normalise datetime to string for JSON serialisation
            if isinstance(doc.get("created_at"), datetime):
                doc["created_at"] = doc["created_at"].isoformat()
            return doc

    # Fallback when no DB or no saved metrics
    return {
        "accuracy": 0.0,
        "precision": 0.0,
        "recall": 0.0,
        "f1_score": 0.0,
        "note": "No trained model metrics yet. Run train_model.py to generate real metrics.",
    }