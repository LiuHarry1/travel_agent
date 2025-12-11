"""Base loader interface."""
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, Any, Optional
from models.document import Document, DocumentType, DocumentStructure
from .utils.file_manager import FileManager
from .utils.image_handler import ImageHandler
from utils.logger import get_logger

logger = get_logger(__name__)


class BaseLoader(ABC):
    """Base class for document loaders."""
    
    def __init__(self, static_dir: str = "static", base_url: str = ""):
        """
        Args:
            static_dir: Static files root directory
            base_url: Base URL for static files
        """
        self.static_dir = Path(static_dir)
        self.base_url = base_url.rstrip('/') if base_url else ""
        self.file_manager = FileManager(self.static_dir)
        self.image_handler = ImageHandler(self.static_dir, self.base_url)
    
    @abstractmethod
    def load(self, source: str, **kwargs) -> Document:
        """Load document from source."""
        pass
    
    @abstractmethod
    def supports(self, doc_type: DocumentType) -> bool:
        """Check if loader supports document type."""
        pass
    
    def _detect_type(self, path: Path) -> DocumentType:
        """Detect document type from file extension."""
        ext = path.suffix.lower()
        type_map = {
            ".pdf": DocumentType.PDF,
            ".docx": DocumentType.DOCX,
            ".doc": DocumentType.DOCX,
            ".html": DocumentType.HTML,
            ".htm": DocumentType.HTML,
            ".md": DocumentType.MARKDOWN,
            ".markdown": DocumentType.MARKDOWN,
            ".txt": DocumentType.TXT,
        }
        return type_map.get(ext, DocumentType.TXT)
    
    def _build_metadata(self, path: Path, file_id: str, saved_source_path: Path, 
                       doc_type: DocumentType, structure: Optional[DocumentStructure] = None,
                       **kwargs) -> Dict[str, Any]:
        """
        Build document metadata.
        
        Args:
            path: Original file path
            file_id: File identifier
            saved_source_path: Path where source file was saved
            doc_type: Document type
            structure: Document structure information
            **kwargs: Additional metadata
        
        Returns:
            Metadata dictionary
        """
        metadata = {
            "file_path": str(path),
            "file_name": path.name,
            "file_size": path.stat().st_size,
            "saved_source_path": str(saved_source_path),
            "file_id": file_id,
            "original_type": doc_type.value,
            **kwargs.get("metadata", {})
        }
        
        # Add structure information
        if structure:
            if structure.total_pages:
                metadata["pages_info"] = structure.total_pages
            
            # Add PDF metadata
            if structure.pdf_metadata:
                for key, value in structure.pdf_metadata.items():
                    if value:
                        metadata[f"pdf_{key}"] = value
        
        return metadata
    
    def _build_document(self, path: Path, content: str, saved_source_path: Path,
                       doc_type: DocumentType, structure: Optional[DocumentStructure] = None,
                       **kwargs) -> Document:
        """
        Build Document object.
        
        Args:
            path: Original file path
            content: Document content (Markdown format)
            saved_source_path: Path where source file was saved
            doc_type: Original document type
            structure: Document structure information
            **kwargs: Additional arguments (may include file_id)
        
        Returns:
            Document object
        """
        file_id = kwargs.pop("file_id", None) or self.file_manager.generate_file_id(path.name)
        metadata = self._build_metadata(path, file_id, saved_source_path, doc_type, structure, **kwargs)
        
        return Document(
            content=content,
            source=str(saved_source_path),
            doc_type=DocumentType.MARKDOWN,  # All loaders convert to Markdown
            metadata=metadata,
            structure=structure
        )

