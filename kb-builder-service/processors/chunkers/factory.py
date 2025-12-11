"""Chunker factory."""
from typing import Dict, Type, Optional
from .base import BaseChunker
from .recursive import RecursiveChunker
from .pdf_chunker import PDFChunker
from .docx_chunker import DOCXChunker
from .html_chunker import HTMLChunker
from .markdown_chunker import MarkdownChunker
from models.document import DocumentType


class ChunkerFactory:
    """Factory for creating document chunkers."""
    
    _chunkers: Dict[DocumentType, Type[BaseChunker]] = {
        DocumentType.PDF: PDFChunker,
        DocumentType.DOCX: DOCXChunker,
        DocumentType.HTML: HTMLChunker,
        DocumentType.MARKDOWN: MarkdownChunker,
        DocumentType.TXT: RecursiveChunker,
    }
    
    @classmethod
    def create(
        cls,
        doc_type: DocumentType,
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
        min_chunk_size: Optional[int] = None,
        **kwargs
    ) -> BaseChunker:
        """Create chunker for document type."""
        chunker_class = cls._chunkers.get(doc_type, RecursiveChunker)
        
        # Set default parameters based on file type
        if doc_type == DocumentType.PDF:
            default_min_size = 100
        elif doc_type == DocumentType.DOCX:
            default_min_size = 150
        else:
            default_min_size = 100
        
        min_size = min_chunk_size if min_chunk_size is not None else default_min_size
        
        return chunker_class(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            min_chunk_size=min_size,
            **kwargs
        )
    
    @classmethod
    def register(cls, doc_type: DocumentType, chunker_class: Type[BaseChunker]):
        """Register a new chunker type."""
        cls._chunkers[doc_type] = chunker_class

