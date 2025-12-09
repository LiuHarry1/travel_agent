"""Parallel retrieval strategy."""
from __future__ import annotations

import asyncio
import logging
from typing import Dict, List

from .base import BaseRetrievalStrategy, RetrievalResult

logger = logging.getLogger(__name__)


class ParallelStrategy(BaseRetrievalStrategy):
    """Strategy that performs parallel retrieval with multiple query variants."""
    
    async def retrieve(
        self,
        query: str,
        conversation_history: List[Dict] = None
    ) -> List[RetrievalResult]:
        """
        Execute parallel retrieval with multiple query variants.
        
        Args:
            query: Base search query
            conversation_history: Conversation history for generating query variants
            
        Returns:
            Merged and deduplicated results from all parallel queries
        """
        num_variants = self.config.get("num_variants", 3)
        
        logger.info(f"Parallel retrieval for query: {query[:50]}, variants: {num_variants}")
        
        # Generate query variants
        query_variants = self._generate_query_variants(query, conversation_history, num_variants)
        
        source = next((s for s in self.sources if hasattr(s, 'config')), self.sources[0])
        pipeline_name = self.config.get("pipeline_name", "default")
        top_k = self.config.get("top_k", 10)
        
        # Execute all queries in parallel
        tasks = [
            source.search(variant, pipeline_name, top_k)
            for variant in query_variants
        ]
        
        results_lists = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Filter out exceptions and collect results
        all_results = []
        for i, result in enumerate(results_lists):
            if isinstance(result, Exception):
                logger.error(f"Parallel query {i+1} failed: {result}")
                continue
            all_results.extend(result)
        
        # Merge and deduplicate
        merged_results = self._deduplicate_results(all_results)
        
        logger.info(f"Parallel retrieval completed: {len(merged_results)} total results from {len(query_variants)} queries")
        return merged_results
    
    def _generate_query_variants(
        self,
        base_query: str,
        conversation_history: List[Dict] = None,
        num_variants: int = 3
    ) -> List[str]:
        """
        Generate query variants for parallel retrieval.
        
        Args:
            base_query: Base query
            conversation_history: Conversation history
            num_variants: Number of variants to generate
            
        Returns:
            List of query variants
        """
        variants = [base_query]  # Always include original
        
        # Extract context from conversation history
        context_terms = []
        if conversation_history:
            for msg in conversation_history[-5:]:  # Last 5 messages
                if msg.get("role") == "user":
                    content = msg.get("content", "")
                    # Extract key terms (simple approach)
                    words = content.split()[:5]  # First 5 words
                    context_terms.extend(words)
        
        # Generate variants by combining base query with context
        if context_terms:
            for i in range(1, num_variants):
                if i <= len(context_terms):
                    variant = f"{base_query} {context_terms[i-1]}"
                    variants.append(variant)
                else:
                    # If not enough context, use base query with different emphasis
                    variants.append(base_query)
        else:
            # If no context, just repeat base query (will be deduplicated)
            variants.extend([base_query] * (num_variants - 1))
        
        # Remove duplicates while preserving order
        seen = set()
        unique_variants = []
        for variant in variants:
            if variant not in seen:
                seen.add(variant)
                unique_variants.append(variant)
        
        return unique_variants[:num_variants]

