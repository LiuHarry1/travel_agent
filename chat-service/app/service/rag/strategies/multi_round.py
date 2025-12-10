"""Multi-round retrieval strategy."""
from __future__ import annotations

import logging
from typing import Dict, List, Optional

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
        min_score_threshold = self.config.get("min_score_threshold", None)  # Optional quality threshold
        
        logger.info(f"Multi-round retrieval for query: {query[:50]}, max_rounds: {max_rounds}")
        
        source = next((s for s in self.sources if hasattr(s, 'config')), self.sources[0])
        pipeline_name = self.config.get("pipeline_name", "default")
        top_k = self.config.get("top_k", 10)
        
        all_results = []
        current_query = query
        previous_results: List[RetrievalResult] = []
        
        for round_num in range(1, max_rounds + 1):
            logger.info(f"Round {round_num}/{max_rounds}: searching with query: {current_query[:50]}")
            
            round_results = await source.search(current_query, pipeline_name, top_k)
            
            # Add round metadata to results
            for result in round_results:
                result.metadata["round"] = round_num
            
            all_results.extend(round_results)
            
            # Deduplicate after each round
            all_results = self._deduplicate_results(all_results)
            
            # Check stopping conditions
            should_stop = False
            
            # Condition 1: Sufficient results by count
            if len(all_results) >= min_results_threshold:
                logger.info(f"Multi-round retrieval: sufficient results ({len(all_results)}) after round {round_num}")
                should_stop = True
            
            # Condition 2: Good quality results (if score threshold is set)
            if min_score_threshold is not None and round_results:
                # Check if we have results with good scores
                # For distance scores, lower is better
                good_results = [r for r in round_results if r.score is not None and r.score <= min_score_threshold]
                if len(good_results) >= min_results_threshold:
                    logger.info(f"Multi-round retrieval: sufficient high-quality results after round {round_num}")
                    should_stop = True
            
            if should_stop:
                break
            
            # If not last round, prepare for next round
            if round_num < max_rounds:
                # Refine query based on previous results
                previous_results = round_results
                refined_query = await self._refine_query_with_results(
                    original_query=query,
                    previous_results=previous_results,
                    conversation_history=conversation_history,
                    round_num=round_num
                )
                
                if refined_query and refined_query != current_query:
                    current_query = refined_query
                    logger.info(f"Query refined for round {round_num + 1}: {current_query[:50]}")
                else:
                    # No improvement possible, stop
                    logger.info(f"No query refinement possible, stopping after round {round_num}")
                    break
        
        logger.info(f"Multi-round retrieval completed: {len(all_results)} total results")
        return all_results
    
    async def _refine_query_with_results(
        self,
        original_query: str,
        previous_results: List[RetrievalResult],
        conversation_history: Optional[List[Dict]] = None,
        round_num: int = 1
    ) -> str:
        """
        Refine query based on previous retrieval results.
        
        Args:
            original_query: Original user query
            previous_results: Results from previous round
            conversation_history: Conversation history for context
            round_num: Current round number
            
        Returns:
            Refined query string
        """
        if not previous_results:
            # No results from previous round, try to expand query
            return self._expand_query(original_query, conversation_history)
        
        # Analyze previous results quality
        scores = [r.score for r in previous_results if r.score is not None]
        if not scores:
            # No scores available, try expansion
            return self._expand_query(original_query, conversation_history)
        
        avg_score = sum(scores) / len(scores)
        min_score = min(scores)
        result_count = len(previous_results)
        
        # Determine refinement strategy based on results
        if result_count < 3:
            # Too few results: expand query
            logger.info(f"Too few results ({result_count}), expanding query")
            return self._expand_query(original_query, conversation_history)
        elif avg_score > 0.5 and min_score > 0.3:
            # Results have high distance (low relevance): refine query
            logger.info(f"Results have low relevance (avg_score={avg_score:.2f}), refining query")
            return self._refine_query(original_query, previous_results, conversation_history)
        else:
            # Results are good, but might need slight adjustment
            # Extract key terms from best results
            best_results = sorted(previous_results, key=lambda x: x.score if x.score is not None else float('inf'))[:3]
            return self._enhance_query_with_results(original_query, best_results, conversation_history)
    
    def _expand_query(self, query: str, conversation_history: Optional[List[Dict]]) -> str:
        """
        Expand query by adding context from conversation history.
        
        Args:
            query: Original query
            conversation_history: Conversation history
            
        Returns:
            Expanded query
        """
        if not conversation_history:
            return query
        
        # Extract key terms from recent conversation
        recent_context = " ".join([
            msg.get("content", "")[:100] 
            for msg in conversation_history[-3:] 
            if msg.get("role") == "user"
        ])
        
        if recent_context:
            return f"{query} {recent_context}"
        return query
    
    def _refine_query(self, query: str, results: List[RetrievalResult], conversation_history: Optional[List[Dict]]) -> str:
        """
        Refine query by adding more specific terms.
        
        Args:
            query: Original query
            results: Previous results
            conversation_history: Conversation history
            
        Returns:
            Refined query
        """
        # Extract key terms from result texts (simple approach)
        # In a more sophisticated implementation, could use LLM or NLP
        key_terms = []
        for result in results[:3]:  # Use top 3 results
            text = result.text[:200]  # First 200 chars
            # Extract potential key terms (simple: first few words)
            words = text.split()[:5]
            key_terms.extend(words)
        
        # Combine with original query
        if key_terms:
            additional_terms = " ".join(set(key_terms[:5]))  # Limit to 5 unique terms
            return f"{query} {additional_terms}"
        
        return query
    
    def _enhance_query_with_results(
        self, 
        query: str, 
        results: List[RetrievalResult], 
        conversation_history: Optional[List[Dict]]
    ) -> str:
        """
        Enhance query with information from best results.
        
        Args:
            query: Original query
            results: Best results from previous round
            conversation_history: Conversation history
            
        Returns:
            Enhanced query
        """
        # For now, return original query (can be enhanced with LLM later)
        return query

