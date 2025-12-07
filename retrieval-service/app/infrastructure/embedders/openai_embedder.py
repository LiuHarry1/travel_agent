"""OpenAI embedder implementation."""
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


class OpenAIEmbedder(BaseEmbedder):
    """OpenAI embedding client."""
    
    def __init__(self, model: str = "text-embedding-3-small", api_key: Optional[str] = None):
        """Initialize OpenAI embedder."""
        if not HAS_OPENAI:
            raise ImportError("openai package is required")
        
        self.model = model
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
        self._client = None
        self._dimension = None
    
    def _get_client(self) -> OpenAI:
        """Get OpenAI client."""
        if self._client is None:
            if not self.api_key:
                raise ValueError("OpenAI API key not found")
            self._client = OpenAI(api_key=self.api_key, base_url=self.base_url)
        return self._client
    
    def embed(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings using OpenAI API."""
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
            logger.error(f"OpenAI embedding error: {e}", exc_info=True)
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
                # Default dimensions for OpenAI models
                if "3-small" in self.model:
                    self._dimension = 1536
                elif "3-large" in self.model:
                    self._dimension = 3072
                else:
                    self._dimension = 1536
        return self._dimension

