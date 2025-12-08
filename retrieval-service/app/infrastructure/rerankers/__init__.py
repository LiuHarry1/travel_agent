"""Reranker implementations."""
from typing import Optional
from app.infrastructure.rerankers.base import BaseReranker
from app.infrastructure.rerankers.api_reranker import APIReranker
from app.infrastructure.rerankers.mock_reranker import MockReranker
from app.infrastructure.config.pipeline_config import RerankConfig

__all__ = [
    "BaseReranker",
    "APIReranker",
    "MockReranker",
    "create_reranker",
]


def create_reranker(config: Optional[RerankConfig]) -> BaseReranker:
    """
    Create reranker instance based on configuration.
    
    Args:
        config: Rerank configuration (None if not configured)
    
    Returns:
        Reranker instance
    """
    if config is None:
        return MockReranker()
    
    if config.api_url and config.api_url.strip():
        try:
            return APIReranker(config)
        except Exception as e:
            from app.utils.logger import get_logger
            logger = get_logger(__name__)
            logger.warning(f"Failed to create API reranker: {e}, falling back to mock")
    
    return MockReranker()
