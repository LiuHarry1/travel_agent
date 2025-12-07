"""Qwen embedder implementation."""
from typing import List, Optional
import os
from app.infrastructure.embedders.base import BaseEmbedder
from app.utils.logger import get_logger

logger = get_logger(__name__)

try:
    from openai import OpenAI
    HAS_OPENAI = True
except ImportError:
    HAS_OPENAI = False


class QwenEmbedder(BaseEmbedder):
    """Qwen embedding client."""
    
    def __init__(self, model: str = "text-embedding-v2", api_key: Optional[str] = None):
        """Initialize Qwen embedder."""
        if not HAS_OPENAI:
            raise ImportError("openai package is required")
        
        self.model = model
        self.api_key = api_key or os.getenv("DASHSCOPE_API_KEY") or os.getenv("QWEN_API_KEY")
        self.base_url = "https://dashscope.aliyuncs.com/compatible-mode/v1"
        self._client = None
        self._dimension = None
    
    def _get_client(self) -> OpenAI:
        """Get OpenAI client."""
        if self._client is None:
            if not self.api_key:
                raise ValueError("Qwen API key not found")
            self._client = OpenAI(api_key=self.api_key, base_url=self.base_url)
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
            
            # Cache dimension from first embedding
            if self._dimension is None and embeddings:
                self._dimension = len(embeddings[0])
            
            return embeddings
        except Exception as e:
            logger.error(f"Qwen embedding error: {e}", exc_info=True)
            raise
    
    @property
    def dimension(self) -> int:
        """Get embedding dimension."""
        if self._dimension is None:
            # Try to get dimension by embedding a test string
            try:
                test_embedding = self.embed(["test"])
                if test_embedding:
                    self._dimension = len(test_embedding[0])
                else:
                    raise ValueError("Could not determine embedding dimension")
            except Exception as e:
                logger.warning(f"Could not determine dimension: {e}")
                # Default dimension for Qwen text-embedding-v2
                self._dimension = 1536
        return self._dimension

