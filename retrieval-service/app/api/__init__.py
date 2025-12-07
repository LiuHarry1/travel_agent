"""API routes."""
from fastapi import APIRouter
from app.api.routes import retrieval, config

router = APIRouter()
router.include_router(retrieval.router, prefix="/retrieval", tags=["retrieval"])
router.include_router(config.router, prefix="/config", tags=["config"])

