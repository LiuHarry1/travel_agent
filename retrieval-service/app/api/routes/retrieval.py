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
    import time
    start_time = time.time()
    logger.info(
        f"Received search request: query={request.query[:100]}, "
        f"pipeline_name={request.pipeline_name}"
    )
    try:
        logger.debug(f"Getting retrieval service for pipeline: {request.pipeline_name}")
        service = get_retrieval_service(request.pipeline_name)
        logger.debug(f"Service obtained, calling retrieve()")
        result = service.retrieve(request.query, return_debug=False)
        elapsed = time.time() - start_time
        logger.info(
            f"Search completed: query={request.query[:100]}, "
            f"results_count={len(result.results) if hasattr(result, 'results') else 0}, "
            f"took {elapsed:.2f}s"
        )
        return result
    except KeyError as e:
        elapsed = time.time() - start_time
        logger.error(f"Pipeline not found: {e} (took {elapsed:.2f}s)", exc_info=True)
        raise HTTPException(status_code=404, detail=f"Pipeline not found: {e}")
    except ValueError as e:
        elapsed = time.time() - start_time
        logger.error(f"Invalid configuration: {e} (took {elapsed:.2f}s)", exc_info=True)
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        elapsed = time.time() - start_time
        logger.error(
            f"Search error: {type(e).__name__}: {e} (took {elapsed:.2f}s)",
            exc_info=True
        )
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")


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

