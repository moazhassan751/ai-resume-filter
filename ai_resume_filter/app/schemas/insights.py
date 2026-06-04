from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ATSScoreRequest(BaseModel):
    resume_text: str = Field(..., min_length=10)
    job_description: str = Field(..., min_length=10)
    category_hint: Optional[str] = None
    candidate_name: Optional[str] = None


class ATSScoreResponse(BaseModel):
    score: int
    confidence: float
    prediction: Optional[str] = None
    matched_keywords: List[str] = []
    missing_keywords: List[str] = []
    summary: str
    bias_flags: List[str] = []


class UploadResponse(BaseModel):
    candidate_name: Optional[str] = None
    candidate_id: Optional[str] = None
    filename: str
    stored_path: str
    extracted_text_length: int
    extraction_confidence: float = 0.0
    ocr_used: bool = False
    ocr_latency_ms: float = 0.0
    pages_processed: int = 0
    preview: str
    ats: Optional[ATSScoreResponse] = None
    semantic_indexed: bool = False


class DocumentIntelligenceResponse(BaseModel):
    filename: str
    extracted_text: str
    extracted_text_length: int
    extraction_confidence: float = 0.0
    ocr_used: bool = False
    ocr_latency_ms: float = 0.0
    pages_processed: int = 0
    source_type: str = "unknown"


class AgentAnalysisRequest(BaseModel):
    resume_text: str = Field(..., min_length=10)
    job_description: Optional[str] = None
    candidate_name: Optional[str] = None


class AgentAnalysisResponse(BaseModel):
    candidate_name: Optional[str] = None
    mode: str
    resume_summary: str
    skill_gaps: List[str]
    bias_flags: List[str]
    hiring_recommendation: str
    crew_output: Optional[Any] = None


class ClassificationReportResponse(BaseModel):
    labels: List[str]
    confusion_matrix: List[List[int]]
    classification_report: Dict[str, Any]
    samples: int
    accuracy: float


class TrainingRunResponse(BaseModel):
    task_id: str
    status: str = "queued"
