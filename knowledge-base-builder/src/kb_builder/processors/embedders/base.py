"""Base embedder interface."""
from abc import ABC, abstractmethod
from typing import List


class BaseEmbedder(ABC):
    """Base class for embedding generators."""
    
    @abstractmethod
    def embed(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for texts."""
        pass
    
    @property
    @abstractmethod
    def dimension(self) -> int:
        """Get embedding dimension."""
        pass

