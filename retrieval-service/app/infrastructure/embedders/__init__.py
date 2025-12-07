"""Embedder implementations."""
from typing import Optional
from app.infrastructure.embedders.base import BaseEmbedder
from app.infrastructure.embedders.qwen_embedder import QwenEmbedder
from app.infrastructure.embedders.bge_embedder import BGEEmbedder
from app.infrastructure.embedders.openai_embedder import OpenAIEmbedder

__all__ = [
    "BaseEmbedder",
    "QwenEmbedder",
    "BGEEmbedder",
    "OpenAIEmbedder",
    "create_embedder",
]


def create_embedder(provider: str, model: Optional[str] = None) -> BaseEmbedder:
    """
    Create embedder instance based on provider.
    
    Args:
        provider: Provider name (qwen, bge, openai)
        model: Optional model name
    
    Returns:
        Embedder instance
    """
    
    provider_lower = provider.lower()
    
    if provider_lower == "qwen":
        model_name = model or "text-embedding-v2"
        return QwenEmbedder(model=model_name)
    elif provider_lower == "bge":
        model_name = model or "BAAI/bge-large-en-v1.5"
        from app.infrastructure.config import settings
        return BGEEmbedder(model=model_name, api_url=settings.bge_api_url)
    elif provider_lower == "openai":
        model_name = model or "text-embedding-3-small"
        return OpenAIEmbedder(model=model_name)
    else:
        raise ValueError(f"Unknown embedder provider: {provider}")
