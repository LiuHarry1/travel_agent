"""LLM filter base implementation."""
from typing import List, Dict, Any
from app.core.services.llm_filter import LLMFilter


class BaseLLMFilter(LLMFilter):
    """Base LLM filter implementation."""
    
    def filter_chunks(
        self,
        query: str,
        chunks: List[Dict[str, Any]],
        top_k: int = 10
    ) -> List[Dict[str, Any]]:
        """Filter chunks using LLM."""
        raise NotImplementedError

