"""Embedder implementations."""
from typing import Optional
import os
from app.infrastructure.embedders.base import BaseEmbedder
from app.infrastructure.embedders.qwen_embedder import QwenEmbedder
from app.infrastructure.embedders.bge_embedder import BGEEmbedder
from app.infrastructure.embedders.openai_embedder import OpenAIEmbedder
from app.infrastructure.embedders.api_embedder import APIEmbedder

__all__ = [
    "BaseEmbedder",
    "QwenEmbedder",
    "BGEEmbedder",
    "OpenAIEmbedder",
    "APIEmbedder",
    "create_embedder",
]


def create_embedder(provider: str, model: Optional[str] = None) -> BaseEmbedder:
    """
    Create embedder instance based on provider.
    
    Args:
        provider: Provider name (qwen, bge, bge-en, bge-zh, openai, nemotron, snowflake)
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
    elif provider_lower == "bge-en":
        # BAAI/bge-large-en-v1.5 with specific API URL
        model_name = model or "BAAI/bge-large-en-v1.5"
        api_url = os.getenv("BGE_EN_API_URL", "http://10.150.115.110:6000")
        return BGEEmbedder(model=model_name, api_url=api_url)
    elif provider_lower == "bge-zh":
        # BAAI/bge-large-zh-v1.5 with specific API URL
        model_name = model or "BAAI/bge-large-zh-v1.5"
        api_url = os.getenv("BGE_ZH_API_URL", "http://10.150.115.110:6001")
        return BGEEmbedder(model=model_name, api_url=api_url)
    elif provider_lower == "nemotron" or provider_lower == "nvidia":
        # nvidia/llama-nemotron-embed-1b-v2
        model_name = model or "nvidia/llama-nemotron-embed-1b-v2"
        api_url = os.getenv("NEMOTRON_API_URL", "http://10.150.115.110:6002/embed")
        # Use "query" type by default for search queries
        return APIEmbedder(api_url=api_url, model=model_name, embedding_type="query")
    elif provider_lower == "snowflake":
        # Snowflake/snowflake-arctic-embed-l
        model_name = model or "Snowflake/snowflake-arctic-embed-l"
        api_url = os.getenv("SNOWFLAKE_API_URL", "http://10.150.115.110:6003/embed")
        # Use "query" type by default for search queries
        return APIEmbedder(api_url=api_url, model=model_name, embedding_type="query")
    elif provider_lower == "openai":
        model_name = model or "text-embedding-3-small"
        return OpenAIEmbedder(model=model_name)
    else:
        raise ValueError(f"Unknown embedder provider: {provider}")
