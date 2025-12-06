"""Retrieval API routes."""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from app.services.retrieval_service import RetrievalService
from app.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter()

# Initialize service (singleton)
_retrieval_service: Optional[RetrievalService] = None


def get_retrieval_service() -> RetrievalService:
    """Get retrieval service instance."""
    global _retrieval_service
    if _retrieval_service is None:
        _retrieval_service = RetrievalService()
    return _retrieval_service


class QueryRequest(BaseModel):
    """Query request model."""
    query: str


class ChunkResult(BaseModel):
    """Chunk result model."""
    chunk_id: int
    text: str


class RetrievalResponse(BaseModel):
    """Retrieval response model."""
    query: str
    results: List[ChunkResult]


class DebugChunkResult(BaseModel):
    """Debug chunk result with scores."""
    chunk_id: int
    text: str
    score: Optional[float] = None
    rerank_score: Optional[float] = None
    embedder: Optional[str] = None


class DebugRetrievalResponse(BaseModel):
    """Debug retrieval response with all steps."""
    query: str
    results: List[ChunkResult]
    debug: Dict[str, Any]


@router.post("/search", response_model=RetrievalResponse)
async def search(request: QueryRequest):
    """
    Search for relevant chunks.
    
    Returns only the final results (chunk_id + text).
    """
    try:
        service = get_retrieval_service()
        result = service.retrieve(request.query, return_debug=False)
        return result
    except Exception as e:
        logger.error(f"Search error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/search/debug", response_model=DebugRetrievalResponse)
async def search_debug(request: QueryRequest):
    """
    Search for relevant chunks with debug information.
    
    Returns all intermediate results for debugging:
    - Results from each embedding model
    - Deduplicated results
    - Re-ranked results
    - Final LLM-filtered results
    """
    try:
        service = get_retrieval_service()
        result = service.retrieve(request.query, return_debug=True)
        return result
    except Exception as e:
        logger.error(f"Search debug error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

