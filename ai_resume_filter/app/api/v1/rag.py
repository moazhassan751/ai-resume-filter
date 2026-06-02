from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import get_current_user
from app.schemas.rag import RagAnalyzeRequest, RagAnalyzeResponse
from app.services.rag_service import get_rag_service

router = APIRouter(prefix="/rag", tags=["rag"])


@router.post("/analyze", response_model=RagAnalyzeResponse)
async def analyze_rag(req: RagAnalyzeRequest, user=Depends(get_current_user)):
    rag = get_rag_service()
    # user can be a namespace or dict depending on test overrides
    requester_email = None
    try:
        requester_email = user.get("email") if hasattr(user, "get") else getattr(user, "email", None)
    except Exception:
        requester_email = None
    try:
        result = await rag.analyze(req.job_description, top_k=req.top_k, requester=requester_email)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

    # Pydantic will validate the payload returned by rag.analyze via the response_model
    return result
