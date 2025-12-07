"""Base reranker implementation."""
from typing import List, Dict, Any
from app.core.services.reranker import Reranker


class BaseReranker(Reranker):
    """Base reranker implementation."""
    
    def rerank(
        self,
        query: str,
        chunks: List[Dict[str, Any]],
        top_k: int = 20
    ) -> List[Dict[str, Any]]:
        """Re-rank chunks."""
        raise NotImplementedError

