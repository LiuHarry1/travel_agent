"""Base chunker interface."""
from abc import ABC, abstractmethod
from typing import List
from ...models.document import Document
from ...models.chunk import Chunk


class BaseChunker(ABC):
    """Base class for text chunkers."""
    
    @abstractmethod
    def chunk(self, document: Document) -> List[Chunk]:
        """Split document into chunks."""
        pass

