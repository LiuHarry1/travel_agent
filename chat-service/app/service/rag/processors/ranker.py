"""Result ranker for sorting retrieval results."""
from __future__ import annotations

import logging
from typing import List

from app.service.rag.sources.base import RetrievalResult

logger = logging.getLogger(__name__)


class ResultRanker:
    """Ranks retrieval results by relevance score."""
    
    def rank(
        self,
        results: List[RetrievalResult],
        strategy: str = "score"
    ) -> List[RetrievalResult]:
        """
        Rank results by specified strategy.
        
        Args:
            results: List of results to rank
            strategy: Ranking strategy ("score", "round", etc.)
            
        Returns:
            Ranked list of results
        """
        if not results:
            return []
        
        if strategy == "score":
            return self._rank_by_score(results)
        elif strategy == "round":
            return self._rank_by_round(results)
        else:
            logger.warning(f"Unknown ranking strategy: {strategy}, using score")
            return self._rank_by_score(results)
    
    def _rank_by_score(self, results: List[RetrievalResult]) -> List[RetrievalResult]:
        """
        Rank results by score (lower is better for distance scores).
        
        Args:
            results: List of results to rank
            
        Returns:
            Ranked list (best score first)
        """
        # Sort by score (lower is better for distance)
        # Handle None scores by putting them at the end
        def sort_key(result: RetrievalResult) -> tuple[float, int]:
            score = result.score if result.score is not None else float('inf')
            # Use chunk_id as tiebreaker for stable sort
            return (score, result.chunk_id)
        
        ranked = sorted(results, key=sort_key)
        logger.info(f"Ranked {len(ranked)} results by score")
        return ranked
    
    def _rank_by_round(self, results: List[RetrievalResult]) -> List[RetrievalResult]:
        """
        Rank results by round (earlier rounds first).
        
        This assumes results have metadata indicating which round they came from.
        
        Args:
            results: List of results to rank
            
        Returns:
            Ranked list (earlier rounds first)
        """
        def sort_key(result: RetrievalResult) -> tuple[int, float]:
            round_num = result.metadata.get("round", 999)  # Default to last if not specified
            score = result.score if result.score is not None else float('inf')
            return (round_num, score)
        
        ranked = sorted(results, key=sort_key)
        logger.info(f"Ranked {len(ranked)} results by round")
        return ranked
