"""Retrieval API routes."""
from fastapi import APIRouter, HTTPException
from app.api.schemas.retrieval import (
    QueryRequest,
    RetrievalResponse,
    DebugRetrievalResponse
)
from app.services.service_factory import get_retrieval_service
from app.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter()


@router.post("/search", response_model=RetrievalResponse)
async def search(request: QueryRequest):
    """
    Search for relevant chunks.
    
    Returns only the final results (chunk_id + text).
    """
    try:
        service = get_retrieval_service(request.pipeline_name)
        result = service.retrieve(request.query, return_debug=False)
        return result
    except KeyError as e:
        logger.error(f"Pipeline not found: {e}")
        raise HTTPException(status_code=404, detail=f"Pipeline not found: {e}")
    except ValueError as e:
        logger.error(f"Invalid configuration: {e}")
        raise HTTPException(status_code=400, detail=str(e))
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
        service = get_retrieval_service(request.pipeline_name)
        result = service.retrieve(request.query, return_debug=True)
        return result
    except KeyError as e:
        logger.error(f"Pipeline not found: {e}")
        raise HTTPException(status_code=404, detail=f"Pipeline not found: {e}")
    except ValueError as e:
        logger.error(f"Invalid configuration: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Search debug error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

