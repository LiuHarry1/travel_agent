"""BGE embedder implementation."""
from typing import List, Optional
import os
from app.infrastructure.embedders.base import BaseEmbedder
from app.utils.logger import get_logger

logger = get_logger(__name__)

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False


class BGEEmbedder(BaseEmbedder):
    """BGE embedding client via API."""
    
    def __init__(self, model: str = "BAAI/bge-large-en-v1.5", api_url: Optional[str] = None):
        """Initialize BGE embedder."""
        if not HAS_REQUESTS:
            raise ImportError("requests package is required")
        
        self.model = model
        self.api_url = api_url or os.getenv("BGE_API_URL", "http://localhost:8001")
        self._dimension = None
    
    def _get_endpoint(self) -> str:
        """Get API endpoint."""
        model_lower = self.model.lower()
        if "bge-large-en" in model_lower or "bge-base-en" in model_lower or "bge-small-en" in model_lower:
            return f"{self.api_url}/embed/en"
        elif "bge-large-zh" in model_lower or "bge-base-zh" in model_lower or "bge-small-zh" in model_lower:
            return f"{self.api_url}/embed/zh"
        else:
            return f"{self.api_url}/embed"
    
    def embed(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings using BGE API."""
        if not texts:
            return []
        
        try:
            endpoint = self._get_endpoint()
            response = requests.post(endpoint, json={"texts": texts}, timeout=300)
            response.raise_for_status()
            result = response.json()
            
            if "embeddings" in result:
                embeddings = result["embeddings"]
            elif "data" in result:
                embeddings = result["data"]
            else:
                embeddings = result if isinstance(result, list) else result.get("embedding", [])
            
            # Cache dimension from first embedding
            if self._dimension is None and embeddings:
                self._dimension = len(embeddings[0])
            
            return embeddings
        except Exception as e:
            logger.error(f"BGE embedding error: {e}", exc_info=True)
            raise
    
    @property
    def dimension(self) -> int:
        """Get embedding dimension."""
        if self._dimension is None:
            dim_map = {
                "BAAI/bge-large-en-v1.5": 1024,
                "BAAI/bge-base-en-v1.5": 768,
                "BAAI/bge-small-en-v1.5": 384,
            }
            self._dimension = dim_map.get(self.model, 1024)
        return self._dimension

