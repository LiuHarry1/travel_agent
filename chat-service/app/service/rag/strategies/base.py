"""Base class for retrieval strategies."""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Dict, List

from ..sources.base import BaseRetrievalSource, RetrievalResult


class BaseRetrievalStrategy(ABC):
    """Base class for all retrieval strategies."""
    
    def __init__(
        self,
        sources: List[BaseRetrievalSource],
        config: Dict
    ):
        """
        Initialize retrieval strategy.
        
        Args:
            sources: List of retrieval sources to use
            config: Strategy-specific configuration
        """
        self.sources = sources
        self.config = config
    
    @abstractmethod
    async def retrieve(
        self,
        query: str,
        conversation_history: List[Dict] = None
    ) -> List[RetrievalResult]:
        """
        Execute retrieval strategy.
        
        Args:
            query: Search query (may be rewritten)
            conversation_history: Conversation history for context
            
        Returns:
            List of RetrievalResult objects
        """
        pass
    
    def _deduplicate_results(
        self,
        results: List[RetrievalResult]
    ) -> List[RetrievalResult]:
        """
        Deduplicate results by chunk_id.
        
        Args:
            results: List of results to deduplicate
            
        Returns:
            Deduplicated list (keeps first occurrence)
        """
        seen = set()
        deduplicated = []
        for result in results:
            if result.chunk_id not in seen:
                seen.add(result.chunk_id)
                deduplicated.append(result)
        return deduplicated
    
    def _merge_results(
        self,
        result_lists: List[List[RetrievalResult]]
    ) -> List[RetrievalResult]:
        """
        Merge multiple result lists and deduplicate.
        
        Args:
            result_lists: List of result lists to merge
            
        Returns:
            Merged and deduplicated results
        """
        all_results = []
        for results in result_lists:
            all_results.extend(results)
        return self._deduplicate_results(all_results)

