from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel


class CandidateInput(BaseModel):
    candidate_id: str
    text: str
    metadata: Optional[dict] = {}


class RankRequest(BaseModel):
    job_description: str
    candidates: List[CandidateInput]


class CandidateOutput(BaseModel):
    candidate_name: Optional[str]
    candidate_id: str
    score: float
    strengths: List[str]
    missing_skills: List[str]
    recommendation: str


class RankResponse(BaseModel):
    results: List[CandidateOutput]
