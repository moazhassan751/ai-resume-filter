"""
API v1 router configuration
"""
from fastapi import APIRouter

api_router = APIRouter()

# Import and include sub-routers here
# from .endpoints import resumes, analysis, users
# api_router.include_router(resumes.router, prefix="/resumes", tags=["resumes"])
# api_router.include_router(analysis.router, prefix="/analysis", tags=["analysis"])
# api_router.include_router(users.router, prefix="/users", tags=["users"])

@api_router.get("/")
async def api_root():
    return {"message": "AI Resume Filter API v1"}
