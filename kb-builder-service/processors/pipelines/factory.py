"""Pipeline factory."""
from typing import Dict, Type, Optional
from models.document import DocumentType
from .base import BasePipeline
from .pdf_pipeline import PDFPipeline
from config.settings import get_settings


class PipelineFactory:
    """Factory for creating document processing pipelines."""
    
    _pipelines: Dict[DocumentType, Type[BasePipeline]] = {
        DocumentType.PDF: PDFPipeline,
    }
    
    @classmethod
    def create(
        cls,
        doc_type: DocumentType,
        static_dir: Optional[str] = None,
        base_url: Optional[str] = None,
        **kwargs
    ) -> BasePipeline:
        """
        Create pipeline for document type.
        
        Args:
            doc_type: Document type
            static_dir: Static files directory (defaults to config)
            base_url: Base URL for static files (defaults to config)
            **kwargs: Additional arguments for pipeline initialization
        
        Returns:
            Pipeline instance
        """
        pipeline_class = cls._pipelines.get(doc_type)
        if not pipeline_class:
            raise ValueError(f"No pipeline available for type: {doc_type}")
        
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
        
        return pipeline_class(static_dir=static_dir, base_url=base_url, **kwargs)
    
    @classmethod
    def register(cls, doc_type: DocumentType, pipeline_class: Type[BasePipeline]):
        """Register a new pipeline type."""
        cls._pipelines[doc_type] = pipeline_class

