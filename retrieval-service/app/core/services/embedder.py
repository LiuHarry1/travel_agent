"""Embedder interface."""
from abc import ABC, abstractmethod
from typing import List


class Embedder(ABC):
    """Interface for embedding models."""
    
    @abstractmethod
    def embed(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for texts.
        
        Args:
            texts: List of text strings to embed
        
        Returns:
            List of embedding vectors
        """
        pass
    
    @property
    @abstractmethod
    def dimension(self) -> int:
        """
        Get embedding dimension.
        
        Returns:
            Dimension of the embedding vectors
        """
        pass

