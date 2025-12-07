"""LLM filter implementations."""
from app.infrastructure.llm.llm_filter import BaseLLMFilter
from app.infrastructure.llm.qwen_filter import QwenLLMFilter
from app.infrastructure.config.pipeline_config import LLMFilterConfig

__all__ = [
    "BaseLLMFilter",
    "QwenLLMFilter",
    "create_llm_filter",
]


def create_llm_filter(config: LLMFilterConfig) -> BaseLLMFilter:
    """
    Create LLM filter instance based on configuration.
    
    Args:
        config: LLM filter configuration
    
    Returns:
        LLM filter instance
    """
    # Currently only Qwen is supported
    return QwenLLMFilter(config)
