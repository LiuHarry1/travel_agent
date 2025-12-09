"""
Base classes and enums for LLM providers.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, AsyncGenerator, Dict, List, Optional

from ..config import get_config


class LLMProvider(str, Enum):
    """Supported LLM providers."""
    QWEN = "qwen"  # Alibaba DashScope
    OPENAI = "openai"  # OpenAI API or OpenAI-compatible API


class LLMError(RuntimeError):
    """Base exception for LLM API errors."""
    pass


class BaseLLMClient(ABC):
    """
    Abstract base class for LLM clients.
    
    Each provider implementation should use their preferred SDK or HTTP client.
    For OpenAI-compatible APIs, use AsyncOpenAI SDK.
    For other providers, use their specific SDK or httpx directly.
    """

    def __init__(self, api_key: Optional[str] = None, config=None):
        """Initialize LLM client."""
        self.api_key = api_key or self._get_api_key()
        self._config = config or get_config()
    
    async def close(self):
        """
        Close client and release resources.
        
        Subclasses should override this to close their specific client instances.
        """
        pass

    @abstractmethod
    def _get_api_key(self) -> Optional[str]:
        """Get API key from environment or config."""
        pass

    @abstractmethod
    def _get_base_url(self) -> str:
        """Get base URL for the API."""
        pass

    @abstractmethod
    def _get_model_name(self) -> str:
        """Get model name from config."""
        pass

    @abstractmethod
    async def _make_stream_request(self, endpoint: str, payload: Dict[str, Any]) -> AsyncGenerator[Any, None]:
        """Make async streaming request to LLM API. Returns async generator of chunks."""
        pass

    @abstractmethod
    def _normalize_payload(self, messages: List[Dict[str, str]], model: Optional[str] = None) -> Dict[str, Any]:
        """Normalize payload format for the specific provider."""
        pass

    @property
    def has_api_key(self) -> bool:
        """Check if API key is available."""
        return bool(self.api_key)

    @property
    def model(self) -> str:
        """Get model name."""
        return self._get_model_name()
