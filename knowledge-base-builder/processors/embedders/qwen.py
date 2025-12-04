"""Qwen (Alibaba DashScope) Embedding client."""
from typing import List, Optional
import os

try:
    from openai import OpenAI
    HAS_OPENAI = True
except ImportError:
    HAS_OPENAI = False

from .base import BaseEmbedder
from utils.exceptions import EmbeddingError
from utils.logger import get_logger

logger = get_logger(__name__)


class QwenEmbedder(BaseEmbedder):
    """
    Qwen Embedding client using DashScope OpenAI-compatible API.
    
    Qwen embedding models:
    - text-embedding-v1: 1536 dimensions
    - text-embedding-v2: 1536 dimensions (recommended)
    """
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "text-embedding-v2",
        base_url: Optional[str] = None
    ):
        """Initialize Qwen embedder."""
        if not HAS_OPENAI:
            raise ImportError(
                "openai package is required. Install with: pip install openai"
            )
        
        self._base_url = base_url
        self.api_key = api_key or self._get_api_key()
        self.model = model
        self._client: Optional[OpenAI] = None
    
    def _get_api_key(self) -> Optional[str]:
        """Get API key from environment variable."""
        return os.getenv("DASHSCOPE_API_KEY") or os.getenv("QWEN_API_KEY")
    
    def _get_base_url(self) -> str:
        """Get DashScope base URL."""
        if self._base_url:
            return self._base_url
        return "https://dashscope.aliyuncs.com/compatible-mode/v1"
    
    def _get_client(self) -> OpenAI:
        """Get or create OpenAI client."""
        if self._client is None:
            if not self.api_key:
                raise EmbeddingError(
                    "Qwen API key not found. Set DASHSCOPE_API_KEY or QWEN_API_KEY environment variable."
                )
            self._client = OpenAI(
                api_key=self.api_key,
                base_url=self._get_base_url()
            )
        return self._client
    
    def embed(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings using Qwen API."""
        if not texts:
            return []
        
        try:
            client = self._get_client()
            response = client.embeddings.create(
                model=self.model,
                input=texts
            )
            embeddings = [item.embedding for item in response.data]
            logger.debug(f"Generated {len(embeddings)} embeddings using Qwen model: {self.model}")
            return embeddings
        except Exception as e:
            logger.error(f"Qwen embedding error: {str(e)}", exc_info=True)
            raise EmbeddingError(f"Qwen embedding failed: {str(e)}") from e
    
    @property
    def dimension(self) -> int:
        """Get embedding dimension for Qwen models."""
        return 1536

