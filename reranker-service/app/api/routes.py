"""API routes."""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from app.services.reranker_service import RerankerService
from app.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter()

# Initialize reranker service
reranker_service = RerankerService()


class RerankRequest(BaseModel):
    """Rerank request model."""
    query: str
    documents: List[str]
    top_k: Optional[int] = None
    model: Optional[str] = None


class RerankResult(BaseModel):
    """Rerank result model."""
    index: int
    relevance_score: float


class RerankResponse(BaseModel):
    """Rerank response model."""
    results: List[RerankResult]


@router.post("/rerank", response_model=RerankResponse)
async def rerank(request: RerankRequest):
    """
    Rerank documents based on query relevance.
    
    Args:
        request: Rerank request with query, documents, and optional top_k
    
    Returns:
        Reranked results with relevance scores
    """
    try:
        if not request.documents:
            return RerankResponse(results=[])
        
        # Use top_k if provided, otherwise return all
        top_k = request.top_k if request.top_k is not None else len(request.documents)
        top_k = min(top_k, len(request.documents))
        
        # Rerank documents
        results = reranker_service.rerank(
            query=request.query,
            documents=request.documents,
            top_k=top_k,
            model=request.model
        )
        
        # Format response
        rerank_results = [
            RerankResult(index=idx, relevance_score=score)
            for idx, score in results
        ]
        
        logger.info(f"Reranked {len(request.documents)} documents, returning top {len(rerank_results)}")
        return RerankResponse(results=rerank_results)
        
    except Exception as e:
        logger.error(f"Rerank error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

