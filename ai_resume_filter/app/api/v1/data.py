from __future__ import annotations

import asyncio
import hashlib
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status as http_status

from app.api.deps import get_current_user
from app.schemas.insights import ATSScoreRequest, ATSScoreResponse, DocumentIntelligenceResponse, UploadResponse
from app.services.document_service import extract_document_intelligence_result, store_upload, validate_upload
from app.core.config import settings
from app.services.embedding_service import get_embedding_service
from app.services.insights_service import score_resume_against_job
from app.services.vector_service import get_vector_service
from services.data_loader import DatasetRegistry
from services.data_service import get_data_service

try:
    from app.services.db import get_db
except Exception:  # pragma: no cover - db is optional in local dev/test
    get_db = None

logger = logging.getLogger(__name__)
router = APIRouter()

_HISTORY_CACHE: List[Dict[str, Any]] = []


@router.get("/status")
async def service_status() -> Dict[str, Any]:
    data_service = get_data_service()
    return {
        "initialized": data_service.loaded,
        "datasets_loaded": len(data_service.list_datasets()),
        "datasets": data_service.list_datasets(),
    }


@router.get("/datasets")
async def datasets() -> Dict[str, Any]:
    return {"registry": DatasetRegistry.list_datasets()}


@router.get("/statistics")
async def statistics() -> Dict[str, Any]:
    data_service = get_data_service()
    if not data_service.loaded:
        await data_service.initialize()
    return {"statistics": data_service.get_dataset_stats()}


@router.post("/upload", response_model=UploadResponse)
async def upload_resume(
    file: UploadFile = File(...),
    candidate_name: Optional[str] = Form(None),
    job_description: Optional[str] = Form(None),
    current_user=Depends(get_current_user),
) -> UploadResponse:
    content = await file.read()
    if not content:
        raise HTTPException(status_code=http_status.HTTP_400_BAD_REQUEST, detail="Uploaded file is empty")
    # Validate upload (size, extension, basic magic checks)
    validate_upload(file.filename, content, max_size=settings.MAX_FILE_SIZE, allowed_extensions=set(settings.ALLOWED_EXTENSIONS))

    upload_dir = Path(settings.UPLOAD_DIR)
    stored_path = store_upload(upload_dir, file.filename, content)
    doc_result = extract_document_intelligence_result(file.filename, content)
    extracted_text = doc_result.text
    logger.info("Upload stored: %s by %s", stored_path, getattr(current_user, 'email', None))

    ats = None
    if job_description:
        ats_data = score_resume_against_job(extracted_text, job_description)
        ats = ATSScoreResponse(**ats_data)

    embedding_service = get_embedding_service()
    vector_service = get_vector_service()
    candidate_id = hashlib.sha256(
        f"{file.filename}|{stored_path.name}|{extracted_text}".encode("utf-8", errors="ignore")
    ).hexdigest()[:24]
    skills = ats.matched_keywords if ats and ats.matched_keywords else embedding_service.extract_skill_candidates(extracted_text)
    category = ats.prediction if ats and ats.prediction else ""

    semantic_metadata = vector_service.build_resume_metadata(
        candidate_id=candidate_id,
        filename=file.filename,
        category=category,
        skills=skills,
        uploaded_by=getattr(current_user, "email", None) if current_user else None,
        text_length=len(extracted_text),
        extra={"candidate_name": candidate_name or ""},
    )
    semantic_indexed = False
    try:
        await asyncio.to_thread(
            vector_service.upsert_document,
            extracted_text,
            candidate_id,
            file.filename,
            semantic_metadata,
        )
        semantic_indexed = True
    except Exception as exc:
        logger.warning("Semantic indexing skipped for %s: %s", file.filename, exc)

    record = {
        "candidate_id": candidate_id,
        "candidate_name": candidate_name,
        "filename": file.filename,
        "stored_path": str(stored_path),
        "extracted_text": extracted_text,
        "extraction_confidence": doc_result.extraction_confidence,
        "ocr_used": doc_result.ocr_used,
        "ocr_latency_ms": doc_result.ocr_latency_ms,
        "pages_processed": doc_result.pages_processed,
        "source_type": doc_result.source_type,
        "uploaded_by": getattr(current_user, "email", None) if current_user else None,
        "job_description": job_description,
        "ats_score": ats.score if ats else None,
        "semantic_indexed": semantic_indexed,
    }
    _HISTORY_CACHE.insert(0, record)

    try:
        db = get_db() if get_db else None
        if db is not None:
            await db.candidate_history.insert_one(record)
    except Exception as exc:
        logger.debug("History persistence skipped: %s", exc)

    return UploadResponse(
        candidate_name=candidate_name,
        candidate_id=candidate_id,
        filename=file.filename,
        stored_path=str(stored_path),
        extracted_text_length=len(extracted_text),
        extraction_confidence=doc_result.extraction_confidence,
        ocr_used=doc_result.ocr_used,
        ocr_latency_ms=doc_result.ocr_latency_ms,
        pages_processed=doc_result.pages_processed,
        preview=extracted_text[:500],
        ats=ats,
        semantic_indexed=semantic_indexed,
    )


@router.post("/intelligence", response_model=DocumentIntelligenceResponse)
async def document_intelligence(
    file: UploadFile = File(...),
    current_user=Depends(get_current_user),
) -> DocumentIntelligenceResponse:
    content = await file.read()
    if not content:
        raise HTTPException(status_code=http_status.HTTP_400_BAD_REQUEST, detail="Uploaded file is empty")
    validate_upload(file.filename, content, max_size=settings.MAX_FILE_SIZE, allowed_extensions=set(settings.ALLOWED_EXTENSIONS))
    doc_result = extract_document_intelligence_result(file.filename, content)
    return DocumentIntelligenceResponse(
        filename=file.filename,
        extracted_text=doc_result.text,
        extracted_text_length=len(doc_result.text),
        extraction_confidence=doc_result.extraction_confidence,
        ocr_used=doc_result.ocr_used,
        ocr_latency_ms=doc_result.ocr_latency_ms,
        pages_processed=doc_result.pages_processed,
        source_type=doc_result.source_type,
    )


@router.post("/ats/score", response_model=ATSScoreResponse)
async def ats_score(body: ATSScoreRequest, current_user=Depends(get_current_user)) -> ATSScoreResponse:
    result = score_resume_against_job(body.resume_text, body.job_description, body.category_hint)
    return ATSScoreResponse(**result)


@router.get("/history")
async def candidate_history(limit: int = 25, current_user=Depends(get_current_user)) -> Dict[str, Any]:
    items: List[Dict[str, Any]] = []
    try:
        db = get_db() if get_db else None
        if db is not None:
            cursor = db.candidate_history.find({}, {"extracted_text": 0}).sort("_id", -1).limit(limit)
            async for item in cursor:
                item.pop("_id", None)
                items.append(item)
    except Exception:
        items = []

    if not items:
        items = [
            {k: v for k, v in record.items() if k != "extracted_text"}
            for record in _HISTORY_CACHE[:limit]
        ]

    return {"items": items}
