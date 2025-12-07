"""Mock reranker implementation."""
from typing import List, Dict, Any
from app.infrastructure.rerankers.base import BaseReranker
from app.utils.logger import get_logger

logger = get_logger(__name__)


class MockReranker(BaseReranker):
    """Mock reranker implementation."""
    
    def rerank(
        self,
        query: str,
        chunks: List[Dict[str, Any]],
        top_k: int = 20
    ) -> List[Dict[str, Any]]:
        """Mock re-ranking implementation."""
        if not chunks:
            return []
        
        logger.info(f"Re-ranking {len(chunks)} chunks (mock implementation)")
        
        # Mock re-ranking: simple keyword matching score
        query_lower = query.lower()
        query_words = set(query_lower.split())
        
        scored_chunks = []
        for chunk in chunks:
            text = chunk.get("text", "").lower()
            text_words = set(text.split())
            
            # Simple overlap score
            overlap = len(query_words & text_words)
            total_words = len(query_words | text_words)
            score = overlap / total_words if total_words > 0 else 0
            
            # Combine with original score (if exists)
            original_score = chunk.get("score", 0.0)
            combined_score = 0.7 * score + 0.3 * (1.0 - original_score)  # Normalize original score
            
            scored_chunks.append({
                **chunk,
                "rerank_score": combined_score
            })
        
        # Sort by rerank score
        scored_chunks.sort(key=lambda x: x["rerank_score"], reverse=True)
        
        # Return top_k
        result = scored_chunks[:top_k]
        logger.info(f"Re-ranked to {len(result)} chunks")
        return result

