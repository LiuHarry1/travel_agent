"""Base location tracker."""
from abc import ABC, abstractmethod
from typing import List
from models.document import Document
from models.chunk import Chunk


class LocationTracker(ABC):
    """Base class for location tracking."""
    
    @abstractmethod
    def track_during_loading(self, document: Document) -> Document:
        """
        Track location information during document loading.
        
        Args:
            document: Document object
        
        Returns:
            Document with location information tracked
        """
        pass
    
    @abstractmethod
    def track_during_chunking(
        self,
        chunks: List[Chunk],
        document: Document
    ) -> List[Chunk]:
        """
        Track and enrich location information during chunking.
        
        Args:
            chunks: List of Chunk objects
            document: Document object
        
        Returns:
            List of Chunks with location information
        """
        pass

