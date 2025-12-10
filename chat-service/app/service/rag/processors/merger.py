"""Result merger for combining results from multiple rounds or parallel searches."""
from __future__ import annotations

import logging
from typing import List, Optional

from app.service.rag.sources.base import RetrievalResult

logger = logging.getLogger(__name__)


class ResultMerger:
    """Merges results from multiple retrieval rounds or parallel searches."""
    
    def merge(
        self,
        result_lists: List[List[RetrievalResult]],
        keep_best_score: bool = True,
        weights: Optional[List[float]] = None
    ) -> List[RetrievalResult]:
        """
        Merge multiple result lists and deduplicate.
        
        Args:
            result_lists: List of result lists to merge (e.g., from multiple rounds)
            keep_best_score: If True, keep the result with the best score when duplicates found
            weights: Optional weights for each result list (for weighted merging)
            
        Returns:
            Merged and deduplicated results
        """
        if not result_lists:
            return []
        
        # Flatten all results
        all_results: List[RetrievalResult] = []
        for i, results in enumerate(result_lists):
            weight = weights[i] if weights and i < len(weights) else 1.0
            for result in results:
                # Apply weight to score if provided
                if weight != 1.0 and result.score is not None:
                    # Create a new result with weighted score
                    weighted_result = RetrievalResult(
                        chunk_id=result.chunk_id,
                        text=result.text,
                        score=result.score * weight,
                        metadata={**result.metadata, "weight": weight}
                    )
                    all_results.append(weighted_result)
                else:
                    all_results.append(result)
        
        # Deduplicate by chunk_id
        seen: dict[int, RetrievalResult] = {}
        for result in all_results:
            chunk_id = result.chunk_id
            
            if chunk_id not in seen:
                seen[chunk_id] = result
            else:
                # Handle duplicate: keep the one with better score
                if keep_best_score:
                    existing = seen[chunk_id]
                    # Compare scores (lower is better for distance, higher is better for similarity)
                    # We assume score is distance (lower is better)
                    existing_score = existing.score if existing.score is not None else float('inf')
                    current_score = result.score if result.score is not None else float('inf')
                    
                    # Keep the one with lower score (better match)
                    if current_score < existing_score:
                        seen[chunk_id] = result
                else:
                    # Keep first occurrence
                    pass
        
        merged = list(seen.values())
        logger.info(
            f"Merged {len(result_lists)} result lists: "
            f"{sum(len(r) for r in result_lists)} total -> {len(merged)} unique results"
        )
        return merged


