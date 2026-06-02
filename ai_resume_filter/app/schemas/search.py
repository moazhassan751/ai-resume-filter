from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class SemanticSearchRequest(BaseModel):
    query: str = Field(..., min_length=1, description="Natural language recruiter query")
    top_k: int = Field(5, ge=1, le=50, description="Maximum number of matches to return")
    category: Optional[str] = Field(None, description="Optional category filter")


class SemanticSearchResult(BaseModel):
    candidate_id: str
    filename: Optional[str] = None
    category: Optional[str] = None
    skills: Optional[str] = None
    timestamp: Optional[str] = None
    score: float = Field(..., ge=0.0, le=1.0)
    preview: str
    explanation: str
    metadata: Dict[str, Any] = Field(default_factory=dict)


class SemanticSearchResponse(BaseModel):
    query: str
    top_k: int
    results: List[SemanticSearchResult]
