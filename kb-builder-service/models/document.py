"""Document model."""
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List, Union
from enum import Enum

from models.structure import (
    BaseStructure,
    PDFStructure,
    DOCXStructure,
    HTMLStructure,
    MarkdownStructure,
)


class DocumentType(str, Enum):
    """Document types."""
    MARKDOWN = "markdown"
    PDF = "pdf"
    DOCX = "docx"
    HTML = "html"
    TXT = "txt"


# Type alias for all structure types
DocumentStructure = Union[
    PDFStructure,
    DOCXStructure,
    HTMLStructure,
    MarkdownStructure,
    BaseStructure,
]


@dataclass
class Document:
    """Document model."""
    content: str
    source: str
    doc_type: DocumentType
    metadata: Dict[str, Any] = field(default_factory=dict)
    structure: Optional[DocumentStructure] = None  # Document structure information
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
    
    def get_location_info(self) -> Dict[str, Any]:
        """Get document location information (for RAG citation)."""
        base_info = {
            "file": self.source,
            "type": self.doc_type.value,
            "file_path": self.metadata.get("file_path")
        }
        
        # Add type-specific information
        if self.structure:
            if isinstance(self.structure, PDFStructure):
                # No page-level info needed in unified Markdown architecture
                pass
            elif isinstance(self.structure, DOCXStructure):
                base_info["total_sections"] = self.structure.total_sections
        
        return base_info

