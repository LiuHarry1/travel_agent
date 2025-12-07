"""Service factory for creating and caching retrieval services."""
from typing import Dict, Optional
from app.services.retrieval_service import RetrievalService
from app.infrastructure.config.pipeline_config import pipeline_config_manager, PipelineConfig
from app.utils.logger import get_logger

logger = get_logger(__name__)

# Service instance cache
_service_cache: Dict[str, RetrievalService] = {}


def get_retrieval_service(pipeline_name: Optional[str] = None) -> RetrievalService:
    """
    Get or create retrieval service instance for a pipeline.
    
    Args:
        pipeline_name: Pipeline name. If None, uses default pipeline.
    
    Returns:
        RetrievalService instance for the pipeline
    
    Raises:
        KeyError: If pipeline not found
        ValueError: If pipeline configuration is invalid
    """
    try:
        # Get pipeline config (auto-reloads if changed)
        pipeline_config = pipeline_config_manager.get_pipeline(pipeline_name)
        cache_key = pipeline_name or pipeline_config_manager.get_pipelines().default
        
        # Check cache
        if cache_key in _service_cache:
            logger.debug(f"Using cached service for pipeline: {cache_key}")
            return _service_cache[cache_key]
        
        # Create new service instance
        logger.info(f"Creating new service instance for pipeline: {cache_key}")
        service = RetrievalService(pipeline_config)
        _service_cache[cache_key] = service
        return service
        
    except KeyError as e:
        logger.error(f"Pipeline not found: {e}")
        raise
    except Exception as e:
        logger.error(f"Failed to create retrieval service: {e}", exc_info=True)
        raise ValueError(f"Failed to create retrieval service: {e}") from e


def clear_cache(pipeline_name: Optional[str] = None) -> None:
    """
    Clear service cache for a pipeline or all pipelines.
    
    Args:
        pipeline_name: Pipeline name to clear. If None, clears all caches.
    """
    if pipeline_name is None:
        logger.info("Clearing all service caches")
        _service_cache.clear()
    else:
        if pipeline_name in _service_cache:
            logger.info(f"Clearing service cache for pipeline: {pipeline_name}")
            del _service_cache[pipeline_name]
        else:
            logger.debug(f"No cache found for pipeline: {pipeline_name}")



