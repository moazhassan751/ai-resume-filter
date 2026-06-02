"""
Data routes: dataset listing, statistics, samples, training splits, semantic search.
Combines rich metadata from v1 with proper HTTP semantics, auth, and Pydantic validation from v2.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field, field_validator

from app.api.deps import get_current_user
from app.services.data_service import get_data_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/data", tags=["data"])


# ── Pydantic request/response models ─────────────────────────────────────────

class TrainingSplitRequest(BaseModel):
    train_ratio: float = Field(0.7, ge=0.1, le=0.9, description="Proportion of data for training")
    val_ratio: float = Field(0.15, ge=0.05, le=0.4, description="Proportion of data for validation")

    @field_validator("val_ratio")
    @classmethod
    def ratios_must_sum_below_one(cls, val_ratio: float, info) -> float:
        train_ratio = info.data.get("train_ratio", 0.7)
        if train_ratio + val_ratio >= 1.0:
            raise ValueError("train_ratio + val_ratio must be less than 1.0")
        return val_ratio


class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1, description="Natural language search query")
    top_k: int = Field(5, ge=1, le=50, description="Number of results to return")


# ── Routes ───────────────────────────────────────────────────────────────────

@router.get("/datasets")
async def list_datasets() -> Dict[str, Any]:
    """List all registered dataset sources with metadata and live load status."""
    svc = get_data_service()
    loaded = svc.list_datasets()

    datasets = {
        "resume_data_csv": {
            "name": "Resume Data CSV",
            "description": "Highly structured resume data with 35 fields",
            "rows": 9544,
            "format": "CSV",
            "use_case": "Skill extraction / model training",
            "status": "ready" if "resume_data_csv" in loaded else "not_loaded",
        },
        "resume_csv": {
            "name": "Resume CSV",
            "description": "Raw resumes with category labels",
            "rows": 2484,
            "format": "CSV",
            "use_case": "Labelled resume classification",
            "status": "ready" if "resume_csv" in loaded else "not_loaded",
        },
        "resumes_jsonl": {
            "name": "Resumes JSONL",
            "description": "Structured JSON resumes",
            "rows": 3500,
            "format": "JSONL",
            "use_case": "JSONL structured resume corpus",
            "status": "ready" if "resumes_jsonl" in loaded else "not_loaded",
        },
        "resume_pdfs": {
            "name": "PDF Resumes",
            "description": "Raw PDF files organised by job category",
            "rows": 2484,
            "format": "PDF",
            "categories": 24,
            "use_case": "PDF parsing / category classification",
            "status": "ready" if "pdf_categories" in loaded else "not_loaded",
        },
        "career_corpus": {
            "name": "Career Corpus",
            "description": "Annotated career data for quality control",
            "rows": 302,
            "format": "Excel",
            "use_case": "Annotated career corpus (quality control)",
            "status": "ready" if "career_corpus" in loaded else "not_loaded",
        },
        "resume_atlas_hf": {
            "name": "Resume Atlas (HuggingFace)",
            "description": "Large pre-curated dataset with 13,389 labelled examples",
            "rows": 13389,
            "format": "HuggingFace Dataset",
            "use_case": "ahmedheakl/resume-atlas — large-scale pretraining",
            "status": "on_demand",
        },
    }

    return {
        "datasets": datasets,
        "loaded_count": len(loaded),
        "total_count": len(datasets),
        "total_records": sum(d.get("rows", 0) for d in datasets.values()),
    }


@router.get("/statistics")
async def dataset_statistics() -> Dict[str, Any]:
    """Return row/column counts and memory usage for every loaded dataset."""
    svc = get_data_service()
    stats = svc.get_dataset_stats()

    return {
        "statistics": stats,
        "summary": {
            "total_loaded": len(stats),
            "total_records": sum(
                s.get("rows", s.get("count", 0)) for s in stats.values()
            ),
        },
    }


@router.get("/status")
async def data_status() -> Dict[str, Any]:
    """Return whether the data service is initialised and which datasets are loaded."""
    svc = get_data_service()
    loaded = svc.list_datasets()

    return {
        "initialized": svc.loaded,
        "datasets_loaded": len(loaded),
        "datasets_available": loaded,
    }


@router.post("/training-split")
async def training_split(
    req: TrainingSplitRequest,
    current_user=Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Generate stratified train / val / test splits from the combined corpus.
    Requires authentication.
    """
    svc = get_data_service()
    if not svc.loaded:
        await svc.initialize()

    try:
        result = await svc.get_training_split(
            train_ratio=req.train_ratio,
            val_ratio=req.val_ratio,
        )
    except Exception as exc:
        logger.exception("Error generating training split: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))

    return result


@router.get("/pdf-categories")
async def get_pdf_categories() -> Dict[str, Any]:
    """Get PDF resume categories and per-category file counts."""
    svc = get_data_service()
    pdf_data = svc.get_dataset("pdf_categories")

    if pdf_data is None:
        raise HTTPException(status_code=404, detail="PDF category data not loaded")

    categories = []
    total = 0
    for cat_name, cat_data in pdf_data.items():
        count = cat_data.get("count", 0)
        categories.append({
            "name": cat_name,
            "count": count,
            "sample_files": cat_data.get("files", [])[:3],
        })
        total += count

    return {
        "categories": sorted(categories, key=lambda x: x["name"]),
        "total_categories": len(categories),
        "total_pdfs": total,
    }


@router.get("/sample")
async def get_sample(
    dataset: str = Query("resume_csv", description="Dataset name to sample from"),
    n: int = Query(5, ge=1, le=100, description="Number of records to return"),
) -> Dict[str, Any]:
    """Return up to *n* normalised records from the requested dataset."""
    import pandas as pd  # local import — only needed here

    svc = get_data_service()
    data = svc.get_dataset(dataset)

    if data is None:
        raise HTTPException(status_code=404, detail=f"Dataset '{dataset}' not loaded")

    try:
        if isinstance(data, pd.DataFrame):
            sample = data.head(n).to_dict(orient="records")
        elif isinstance(data, list):
            sample = data[:n]
        elif isinstance(data, dict) and "records" in data:
            sample = data["records"][:n]
        else:
            sample = []
    except Exception as exc:
        logger.exception("Error sampling dataset '%s': %s", dataset, exc)
        raise HTTPException(status_code=500, detail=str(exc))

    return {"dataset": dataset, "count": len(sample), "records": sample}


@router.post("/search")
async def semantic_search(req: SearchRequest) -> Dict[str, Any]:
    """
    Run a cosine-similarity search over the ChromaDB resume index.
    Returns the top-k most semantically similar resumes.
    """
    try:
        from app.services.embeddings_service import EmbeddingsService
        from app.core.config import settings

        svc = EmbeddingsService(persist_dir=settings.CHROMA_PERSIST_DIRECTORY)
        svc.load_model()
        results = svc.query(req.query, top_k=req.top_k)
    except Exception as exc:
        logger.exception("Semantic search error: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))

    return {"query": req.query, "top_k": req.top_k, "results": results}