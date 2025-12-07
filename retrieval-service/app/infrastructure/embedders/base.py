"""Base embedder implementation."""
from typing import List
from app.core.services.embedder import Embedder


class BaseEmbedder(Embedder):
    """Base embedder implementation."""
    
    def embed(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings."""
        raise NotImplementedError
    
    @property
    def dimension(self) -> int:
        """Get embedding dimension."""
        raise NotImplementedError

