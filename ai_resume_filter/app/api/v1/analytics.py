from __future__ import annotations

from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import get_current_user
from app.schemas.analytics import (
    AnalyticsDashboardResponse,
    ExplainabilityRequest,
    ExplainabilityResponse,
    RecruiterInsightsResponse,
)
from app.services.db import get_db
from app.services.explainability_service import build_explainability_payload, build_recruiter_insights
from app.services.insights_service import build_classification_report

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.post("/explain", response_model=ExplainabilityResponse)
async def explainability(request: ExplainabilityRequest, current_user=Depends(get_current_user)):
    try:
        payload = build_explainability_payload(
            request.resume_text,
            request.job_description,
            request.category_hint,
        )
        return ExplainabilityResponse(**payload)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/recruiter-insights", response_model=RecruiterInsightsResponse)
async def recruiter_insights(current_user=Depends(get_current_user)):
    try:
        db = get_db()
    except Exception:
        db = None

    ranking_results: List[Dict[str, Any]] = []
    upload_metrics: Dict[str, Any] = {}

    if db is not None:
        try:
            cursor = db.candidate_history.find({}, {"extracted_text": 0}).sort("_id", -1).limit(25)
            async for item in cursor:
                if isinstance(item, dict):
                    ranking_results.append({
                        "candidate_id": item.get("candidate_id"),
                        "candidate_name": item.get("candidate_name"),
                        "score": float(item.get("ats_score") or 0.0),
                        "semantic_indexed": bool(item.get("semantic_indexed")),
                    })
        except Exception:
            ranking_results = []

    upload_metrics.update({
        "applied": len(ranking_results),
        "screened": len(ranking_results),
        "interviewed": sum(1 for row in ranking_results if row.get("score", 0.0) >= 80),
        "hired": sum(1 for row in ranking_results if row.get("score", 0.0) >= 90),
    })

    for row in ranking_results:
        upload_metrics.setdefault("semantic_similarity", 0.0)
        upload_metrics.setdefault("ats_keyword", 0.0)
        upload_metrics.setdefault("skill_overlap", 0.0)
        upload_metrics.setdefault("experience_relevance", 0.0)
        upload_metrics.setdefault("education_relevance", 0.0)

    insights = build_recruiter_insights(ranking_results, upload_metrics)
    return RecruiterInsightsResponse(**insights)


@router.get("/dashboard", response_model=AnalyticsDashboardResponse)
async def analytics_dashboard(current_user=Depends(get_current_user)):
    report = await build_classification_report()
    recruiter = await recruiter_insights(current_user=current_user)
    model_metrics: Dict[str, Any] = {
        "accuracy": report.get("accuracy"),
        "samples": report.get("samples"),
    }

    category_distribution = [
        {"name": label, "value": float(index + 1) * 12.5}
        for index, label in enumerate(report.get("labels", []))
    ]
    semantic_series = [
        {"name": "Strong", "value": float(recruiter.summary.get("strong_matches", 0)) * 25.0},
        {"name": "Watchlist", "value": float(recruiter.summary.get("watchlist", 0)) * 15.0},
        {"name": "Weak", "value": float(recruiter.summary.get("weak_matches", 0)) * 10.0},
    ]

    chart_data = {
        "funnel": [
            {"name": "Applied", "value": recruiter.hiring_funnel.get("applied", 0)},
            {"name": "Screened", "value": recruiter.hiring_funnel.get("screened", 0)},
            {"name": "Interviewed", "value": recruiter.hiring_funnel.get("interviewed", 0)},
            {"name": "Hired", "value": recruiter.hiring_funnel.get("hired", 0)},
        ],
        "score_breakdown": recruiter.score_breakdown,
        "confusion_matrix": {
            "labels": report.get("labels", []),
            "matrix": report.get("confusion_matrix", []),
        },
        "category_distribution": category_distribution,
        "semantic_similarity": semantic_series,
    }

    explainability_samples: List[Dict[str, Any]] = []
    if report.get("labels"):
        explainability_samples = [{"label": label, "weight": 1.0 / max(len(report["labels"]), 1)} for label in report["labels"]]

    return AnalyticsDashboardResponse(
        model_metrics=model_metrics,
        classification_report=report,
        recruiter_insights=recruiter.model_dump(),
        explainability_samples=explainability_samples,
        chart_data=chart_data,
    )