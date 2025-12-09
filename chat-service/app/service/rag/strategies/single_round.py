"""Single round retrieval strategy."""
from __future__ import annotations

import logging
from typing import Dict, List

from .base import BaseRetrievalStrategy, RetrievalResult

logger = logging.getLogger(__name__)


class SingleRoundStrategy(BaseRetrievalStrategy):
    """Strategy that performs a single round of retrieval."""
    
    async def retrieve(
        self,
        query: str,
        conversation_history: List[Dict] = None
    ) -> List[RetrievalResult]:
        """
        Execute single round retrieval.
        
        Args:
            query: Search query
            conversation_history: Not used in single round strategy
            
        Returns:
            List of RetrievalResult objects
        """
        logger.info(f"Single round retrieval for query: {query[:50]}")
        
        # Use the first enabled source
        source = next((s for s in self.sources if hasattr(s, 'config')), self.sources[0])
        
        pipeline_name = self.config.get("pipeline_name", "default")
        top_k = self.config.get("top_k", 10)
        
        results = await source.search(query, pipeline_name, top_k)
        
        logger.info(f"Single round retrieval returned {len(results)} results")
        return results

