"""LLM filter implementations."""
from typing import Optional
from app.infrastructure.llm.llm_filter import BaseLLMFilter
from app.infrastructure.llm.qwen_filter import QwenLLMFilter
from app.infrastructure.config.pipeline_config import LLMFilterConfig

__all__ = [
    "BaseLLMFilter",
    "QwenLLMFilter",
    "create_llm_filter",
]


class MockLLMFilter(BaseLLMFilter):
    """Mock LLM filter that returns chunks as-is (no filtering)."""
    
    def filter_chunks(
        self,
        query: str,
        chunks: list,
        top_k: int = 10
    ) -> list:
        """Return chunks as-is without filtering."""
        return chunks[:top_k]


def create_llm_filter(config: Optional[LLMFilterConfig]) -> BaseLLMFilter:
    """
    Create LLM filter instance based on configuration.
    
    Args:
        config: LLM filter configuration (None if not configured)
    
    Returns:
        LLM filter instance
    """
    if config is None:
        return MockLLMFilter()
    
    # If base_url and model are empty, return mock filter
    if (not config.base_url or not config.base_url.strip()) and \
       (not config.model or not config.model.strip()):
        return MockLLMFilter()
    
    # Currently only Qwen is supported
    try:
        return QwenLLMFilter(config)
    except Exception as e:
        from app.utils.logger import get_logger
        logger = get_logger(__name__)
        logger.warning(f"Failed to create LLM filter: {e}, falling back to mock")
        return MockLLMFilter()
