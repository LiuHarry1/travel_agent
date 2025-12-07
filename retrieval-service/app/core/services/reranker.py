"""Reranker interface."""
from abc import ABC, abstractmethod
from typing import List, Dict, Any


class Reranker(ABC):
    """Interface for reranking models."""
    
    @abstractmethod
    def rerank(
        self,
        query: str,
        chunks: List[Dict[str, Any]],
        top_k: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Re-rank chunks based on query relevance.
        
        Args:
            query: User query
            chunks: List of chunks with chunk_id, text, and score
            top_k: Number of top results to return
        
        Returns:
            Re-ranked list of chunks with rerank_score
        """
        pass

