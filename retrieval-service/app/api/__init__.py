"""API routes."""
from fastapi import APIRouter
from app.api.routes import retrieval

router = APIRouter()
router.include_router(retrieval.router, prefix="/retrieval", tags=["retrieval"])

