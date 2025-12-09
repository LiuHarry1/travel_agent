"""Base class for retrieval sources."""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


class RetrievalResult:
    """Result from a retrieval source."""
    
    def __init__(
        self,
        chunk_id: int,
        text: str,
        score: Optional[float] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        self.chunk_id = chunk_id
        self.text = text
        self.score = score
        self.metadata = metadata or {}
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        result = {
            "chunk_id": self.chunk_id,
            "text": self.text
        }
        if self.score is not None:
            result["score"] = self.score
        if self.metadata:
            result["metadata"] = self.metadata
        return result


class BaseRetrievalSource(ABC):
    """Base class for all retrieval sources."""
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize retrieval source.
        
        Args:
            config: Source-specific configuration
        """
        self.config = config
    
    @abstractmethod
    async def search(
        self,
        query: str,
        pipeline_name: str = "default",
        top_k: int = 10
    ) -> List[RetrievalResult]:
        """
        Search for relevant documents.
        
        Args:
            query: Search query
            pipeline_name: Pipeline name (if applicable)
            top_k: Maximum number of results to return
            
        Returns:
            List of RetrievalResult objects
        """
        pass
    
    @abstractmethod
    def get_source_type(self) -> str:
        """Get the type identifier of this source."""
        pass

