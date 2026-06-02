from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.deps import get_current_user
from app.schemas.insights import AgentAnalysisRequest, AgentAnalysisResponse
from app.services.insights_service import run_multi_agent_analysis

router = APIRouter()


@router.post("/analyze", response_model=AgentAnalysisResponse)
async def analyze_resume(body: AgentAnalysisRequest, current_user=Depends(get_current_user)) -> AgentAnalysisResponse:
    result = run_multi_agent_analysis(body.resume_text, body.job_description)
    return AgentAnalysisResponse(candidate_name=body.candidate_name, **result)
