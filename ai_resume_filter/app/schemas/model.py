from __future__ import annotations
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, model_validator


class ResumeInput(BaseModel):
    """Expected fields for a single resume prediction request."""
    resume_text: str = Field(..., min_length=10, description="Raw resume text")
    category_hint: Optional[str] = Field(None, description="Optional category hint")


class PredictRequest(BaseModel):
    data: ResumeInput  # typed, not Dict[str, Any]
    top_k: int = Field(5, ge=1, le=20, description="Number of top predictions to return")


class PredictResponse(BaseModel):
    prediction: str                                  # the top predicted job category
    confidence: float = Field(..., ge=0.0, le=1.0)  # confidence of top prediction
    probabilities: Optional[Dict[str, float]] = None
    top_keywords: Optional[List[str]] = None

    model_config = {"from_attributes": True}


class Metrics(BaseModel):
    task: str = Field(..., min_length=1)
    metrics: Dict[str, float]
    details: Optional[Dict[str, Any]] = None

    @model_validator(mode="after")
    def metrics_not_empty(self) -> Metrics:
        if not self.metrics:
            raise ValueError("metrics dict cannot be empty")
        return self

    model_config = {"from_attributes": True}

