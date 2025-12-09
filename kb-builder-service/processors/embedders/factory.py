"""Embedder factory."""
from typing import Optional
import os
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
        
        # Get timeout from settings if not provided in kwargs
        if "timeout" not in kwargs:
            try:
                from config.settings import get_settings
                settings = get_settings()
                kwargs["timeout"] = settings.embedding_timeout
            except:
                kwargs["timeout"] = 300  # Default 5 minutes
        
        if provider == "qwen":
            # Use default model if not provided
            qwen_model = model or "text-embedding-v2"
            return QwenEmbedder(model=qwen_model, **kwargs)
        elif provider == "openai":
            # OpenAI requires a model, use default if not provided
            openai_model = model or "text-embedding-3-small"
            return OpenAIEmbedder(model=openai_model, **kwargs)
        elif provider == "bge":
            # Check for API URL in kwargs, environment variable, or settings
            api_url = kwargs.get("api_url") or os.getenv("BGE_API_URL")
            if not api_url:
                try:
                    from config.settings import get_settings
                    settings = get_settings()
                    api_url = settings.bge_api_url or None
                except:
                    pass
            
            return BGEEmbedder(
                model_name=model or "BAAI/bge-large-en-v1.5",
                api_url=api_url,
                **{k: v for k, v in kwargs.items() if k != "api_url"}
            )
        else:
            raise ValueError(f"Unknown embedder provider: {provider}")

