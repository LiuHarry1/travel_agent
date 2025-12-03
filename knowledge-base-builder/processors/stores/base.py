"""Base vector store interface."""
from abc import ABC, abstractmethod
from typing import List
from models.chunk import Chunk


class BaseVectorStore(ABC):
    """Base class for vector stores."""
    
    @abstractmethod
    def index(self, chunks: List[Chunk], collection_name: str) -> int:
        """Index chunks to vector store."""
        pass

