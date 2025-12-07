"""LLM filter interface."""
from abc import ABC, abstractmethod
from typing import List, Dict, Any


class LLMFilter(ABC):
    """Interface for LLM-based chunk filtering."""
    
    @abstractmethod
    def filter_chunks(
        self,
        query: str,
        chunks: List[Dict[str, Any]],
        top_k: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Filter chunks using LLM to determine relevance.
        
        Args:
            query: User query
            chunks: List of chunks with chunk_id and text
            top_k: Number of chunks to return
        
        Returns:
            Filtered list of relevant chunks
        """
        pass

