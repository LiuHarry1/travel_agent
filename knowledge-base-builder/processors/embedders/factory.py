"""Embedder factory."""
from typing import Optional
from .base import BaseEmbedder
from .qwen import QwenEmbedder
from .openai import OpenAIEmbedder
from .bge import BGEEmbedder


class EmbedderFactory:
    """Factory for creating embedders."""
    
    @staticmethod
    def create(
        provider: str,
        model: Optional[str] = None,
        **kwargs
    ) -> BaseEmbedder:
        """Create embedder by provider name."""
        provider = provider.lower()
        
        if provider == "qwen":
            return QwenEmbedder(model=model, **kwargs)
        elif provider == "openai":
            return OpenAIEmbedder(model=model, **kwargs)
        elif provider == "bge":
            return BGEEmbedder(model_name=model or "BAAI/bge-large-en-v1.5", **kwargs)
        else:
            raise ValueError(f"Unknown embedder provider: {provider}")

