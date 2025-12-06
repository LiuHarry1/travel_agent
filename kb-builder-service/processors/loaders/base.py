"""Base loader interface."""
from abc import ABC, abstractmethod
from models.document import Document, DocumentType


class BaseLoader(ABC):
    """Base class for document loaders."""
    
    @abstractmethod
    def load(self, source: str, **kwargs) -> Document:
        """Load document from source."""
        pass
    
    @abstractmethod
    def supports(self, doc_type: DocumentType) -> bool:
        """Check if loader supports document type."""
        pass

