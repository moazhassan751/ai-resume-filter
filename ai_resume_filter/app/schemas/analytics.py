from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ExplainabilityRequest(BaseModel):
    resume_text: str = Field(..., min_length=10)
    job_description: Optional[str] = None
    category_hint: Optional[str] = None


class ExplainabilityResponse(BaseModel):
    prediction: Optional[str] = None
    prediction_confidence: float
    semantic_overlap: float
    top_tfidf_features: List[Dict[str, Any]]
    feature_importance: List[Dict[str, Any]]
    shap_explanations: List[Dict[str, Any]]
    top_keywords: List[str]
    matched_terms: List[str]
    skill_gaps: List[str]
    summary: str


class RecruiterInsightsResponse(BaseModel):
    summary: Dict[str, Any]
    upload_metrics: Dict[str, Any]
    hiring_funnel: Dict[str, Any]
    score_breakdown: Dict[str, Any]


class AnalyticsDashboardResponse(BaseModel):
    model_metrics: Dict[str, Any]
    classification_report: Dict[str, Any]
    recruiter_insights: Dict[str, Any]
    explainability_samples: List[Dict[str, Any]]
    chart_data: Dict[str, Any]
