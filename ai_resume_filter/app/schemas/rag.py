from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel


class RagAnalyzeRequest(BaseModel):
    job_description: str
    top_k: int = 10


class RankedCandidate(BaseModel):
    candidate_id: str
    score: float
    reasons: Optional[List[str]] = []
    strengths: Optional[List[str]] = []
    missing_skills: Optional[List[str]] = []


class SkillGap(BaseModel):
    skill: str
    missing_from: Optional[List[str]] = []


class RagDiagnostics(BaseModel):
    retrieval_ms: float
    ai_ms: float
    total_ms: float
    used_model: Optional[str]
    fallback: bool = False


class RagAnalyzeResponse(BaseModel):
    ranked_candidates: List[RankedCandidate]
    summary: str
    recommended_hires: List[str]
    skill_gaps: List[SkillGap]
    diagnostics: RagDiagnostics
