"""Generic API embedder implementation for HTTP-based embedding services."""
from typing import List, Optional, Literal
from app.infrastructure.embedders.base import BaseEmbedder
from app.utils.logger import get_logger

logger = get_logger(__name__)

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False


class APIEmbedder(BaseEmbedder):
    """Generic API-based embedder for HTTP embedding services."""
    
    def __init__(
        self,
        api_url: str,
        model: str = "unknown",
        embedding_type: Optional[Literal["query", "passage"]] = None,
        dimension: Optional[int] = None,
        timeout: int = 300
    ):
        """
        Initialize API embedder.
        
        Args:
            api_url: Full API endpoint URL
            model: Model name (for logging)
            embedding_type: Optional type parameter ("query" or "passage")
            dimension: Optional embedding dimension (will be auto-detected if None)
            timeout: Request timeout in seconds
        """
        if not HAS_REQUESTS:
            raise ImportError("requests package is required")
        
        self.api_url = api_url
        self.model = model
        self.embedding_type = embedding_type
        self._dimension = dimension
        self.timeout = timeout
    
    def embed(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings using API."""
        if not texts:
            return []
        
        try:
            # Build request payload
            payload = {"texts": texts}
            if self.embedding_type:
                payload["type"] = self.embedding_type
            
            response = requests.post(
                self.api_url,
                json=payload,
                timeout=self.timeout
            )
            response.raise_for_status()
            result = response.json()
            
            # Extract embeddings from response
            if "embeddings" in result:
                embeddings = result["embeddings"]
            elif "data" in result:
                embeddings = result["data"]
            elif isinstance(result, list):
                embeddings = result
            else:
                embeddings = result.get("embedding", [])
            
            # Cache dimension from first embedding
            if self._dimension is None and embeddings:
                self._dimension = len(embeddings[0])
            
            return embeddings
        except Exception as e:
            logger.error(f"API embedding error for {self.model}: {e}", exc_info=True)
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
                logger.warning(f"Could not determine dimension for {self.model}: {e}")
                # Default dimension (will be updated on first real embedding)
                self._dimension = 1024
        return self._dimension

