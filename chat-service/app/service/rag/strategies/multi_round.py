"""Multi-round retrieval strategy."""
from __future__ import annotations

import logging
from typing import Dict, List

from .base import BaseRetrievalStrategy, RetrievalResult

logger = logging.getLogger(__name__)


class MultiRoundStrategy(BaseRetrievalStrategy):
    """Strategy that performs multiple rounds of retrieval."""
    
    async def retrieve(
        self,
        query: str,
        conversation_history: List[Dict] = None
    ) -> List[RetrievalResult]:
        """
        Execute multi-round retrieval.
        
        Args:
            query: Initial search query
            conversation_history: Conversation history for context
            
        Returns:
            List of RetrievalResult objects from all rounds
        """
        max_rounds = self.config.get("max_rounds", 3)
        min_results_threshold = self.config.get("min_results_threshold", 3)
        
        logger.info(f"Multi-round retrieval for query: {query[:50]}, max_rounds: {max_rounds}")
        
        source = next((s for s in self.sources if hasattr(s, 'config')), self.sources[0])
        pipeline_name = self.config.get("pipeline_name", "default")
        top_k = self.config.get("top_k", 10)
        
        all_results = []
        current_query = query
        
        for round_num in range(1, max_rounds + 1):
            logger.info(f"Round {round_num}/{max_rounds}: searching with query: {current_query[:50]}")
            
            round_results = await source.search(current_query, pipeline_name, top_k)
            all_results.extend(round_results)
            
            # Deduplicate after each round
            all_results = self._deduplicate_results(all_results)
            
            # Check if we have enough results
            if len(all_results) >= min_results_threshold:
                logger.info(f"Multi-round retrieval: sufficient results after round {round_num}")
                break
            
            # If not last round, prepare for next round
            if round_num < max_rounds:
                # Generate a refined query for next round
                # For now, we'll use a simple approach: add context from conversation
                # In a more sophisticated implementation, this could use LLM to refine
                if conversation_history and len(conversation_history) > 0:
                    # Extract key terms from recent conversation
                    recent_context = " ".join([
                        msg.get("content", "")[:100] 
                        for msg in conversation_history[-3:] 
                        if msg.get("role") == "user"
                    ])
                    if recent_context:
                        current_query = f"{query} {recent_context}"
                else:
                    # If no more context, stop
                    break
        
        logger.info(f"Multi-round retrieval completed: {len(all_results)} total results")
        return all_results

