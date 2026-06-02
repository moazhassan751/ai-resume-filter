"""API v1 router — aggregates auth, model, data, search, and agent sub-routers."""
from fastapi import APIRouter

from app.api.v1 import agents, analytics, auth, data, model, search, rag, ranking

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(model.router, prefix="/model", tags=["model"])
api_router.include_router(data.router, prefix="/data", tags=["data"])
api_router.include_router(search.router, tags=["search"])
api_router.include_router(agents.router, prefix="/agents", tags=["agents"])
api_router.include_router(rag.router, tags=["rag"])
api_router.include_router(ranking.router, tags=["ranking"])
api_router.include_router(analytics.router, tags=["analytics"])


@api_router.get("/", tags=["root"])
async def api_root():
    return {"message": "TalentLens AI API v1"}