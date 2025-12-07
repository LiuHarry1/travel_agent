"""Vector store interface."""
from abc import ABC, abstractmethod
from typing import List, Optional, Any


class VectorStore(ABC):
    """Interface for vector database operations."""
    
    @abstractmethod
    def search(
        self,
        query_vectors: List[List[float]],
        anns_field: str = "embedding",
        limit: int = 10,
        output_fields: Optional[List[str]] = None,
        collection_name: Optional[str] = None,
    ) -> Optional[List[Any]]:
        """
        Search for similar vectors.
        
        Args:
            query_vectors: Query vectors to search
            anns_field: Field name for vector search
            limit: Number of results to return
            output_fields: Fields to return in results
            collection_name: Collection name to search
        
        Returns:
            List of search results
        """
        pass

