"""Loader factory."""
from typing import Dict, Type, Optional
from .base import BaseLoader
from .pdf.pdf_loader import PDFLoader
from .docx.docx_loader import DOCXLoader
from .html.html_loader import HTMLLoader
from .markdown.markdown_loader import MarkdownLoader
from .txt.txt_loader import TXTLoader
from models.document import DocumentType
from config.settings import get_settings


class LoaderFactory:
    """Factory for creating document loaders."""
    
    _loaders: Dict[DocumentType, Type[BaseLoader]] = {
        DocumentType.PDF: PDFLoader,
        DocumentType.DOCX: DOCXLoader,
        DocumentType.HTML: HTMLLoader,
        DocumentType.MARKDOWN: MarkdownLoader,
        DocumentType.TXT: TXTLoader,
    }
    
    @classmethod
    def create(
        cls, 
        doc_type: DocumentType, 
        static_dir: Optional[str] = None, 
        base_url: Optional[str] = None
    ) -> BaseLoader:
        """
        Create loader for document type.
        
        Args:
            doc_type: Document type
            static_dir: Static files directory (defaults to config)
            base_url: Base URL for static files (defaults to config)
        
        Returns:
            Loader instance
        """
        loader_class = cls._loaders.get(doc_type)
        if not loader_class:
            raise ValueError(f"No loader available for type: {doc_type}")
        
        # Get defaults from config if not provided
        if static_dir is None or base_url is None:
            try:
                settings = get_settings()
                if static_dir is None:
                    static_dir = getattr(settings, 'static_dir', 'static')
                if base_url is None:
                    base_url = getattr(settings, 'static_base_url', '')
            except Exception:
                if static_dir is None:
                    static_dir = 'static'
                if base_url is None:
                    base_url = ''
        
        return loader_class(static_dir=static_dir, base_url=base_url)
    
    @classmethod
    def register(cls, doc_type: DocumentType, loader_class: Type[BaseLoader]):
        """Register a new loader type."""
        cls._loaders[doc_type] = loader_class

