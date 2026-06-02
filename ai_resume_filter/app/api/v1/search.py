from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import get_current_user
from app.schemas.search import SemanticSearchRequest, SemanticSearchResponse, SemanticSearchResult
from app.services.vector_service import get_vector_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/search", tags=["search"])


@router.post("/semantic", response_model=SemanticSearchResponse)
async def semantic_search(
    request: SemanticSearchRequest,
    current_user=Depends(get_current_user),
) -> SemanticSearchResponse:
    try:
        vector_service = get_vector_service()
        if request.category:
            results = vector_service.search(
                request.query,
                top_k=request.top_k,
                where={"category": request.category},
            )
        else:
            results = vector_service.search(request.query, top_k=request.top_k)
    except Exception as exc:
        logger.exception("Semantic search error: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))

    return SemanticSearchResponse(
        query=request.query,
        top_k=request.top_k,
        results=[SemanticSearchResult(**result) for result in results],
    )
