"""Loader factory."""
from typing import Dict, Type
from .base import BaseLoader
from .markdown import MarkdownLoader
from models.document import DocumentType


class LoaderFactory:
    """Factory for creating document loaders."""
    
    _loaders: Dict[DocumentType, Type[BaseLoader]] = {
        DocumentType.MARKDOWN: MarkdownLoader,
    }
    
    @classmethod
    def create(cls, doc_type: DocumentType) -> BaseLoader:
        """Create loader for document type."""
        loader_class = cls._loaders.get(doc_type)
        if not loader_class:
            raise ValueError(f"No loader available for type: {doc_type}")
        return loader_class()
    
    @classmethod
    def register(cls, doc_type: DocumentType, loader_class: Type[BaseLoader]):
        """Register a new loader type."""
        cls._loaders[doc_type] = loader_class

