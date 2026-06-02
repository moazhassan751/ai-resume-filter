from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import get_current_user
from app.schemas.ranking import RankRequest, RankResponse, CandidateOutput
from app.services.ranking_service import get_ranking_service

router = APIRouter(prefix="/ranking", tags=["ranking"])


@router.post("/rank-candidates", response_model=RankResponse)
async def rank_candidates(req: RankRequest, user=Depends(get_current_user)):
    svc = get_ranking_service()
    try:
        ranked = svc.score_candidates(req.job_description, [c.dict() for c in req.candidates])
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

    out = [
        CandidateOutput(
            candidate_name=r.candidate_name,
            candidate_id=r.candidate_id,
            score=r.score,
            strengths=r.strengths,
            missing_skills=r.missing_skills,
            recommendation=r.recommendation,
        )
        for r in ranked
    ]

    return RankResponse(results=out)
