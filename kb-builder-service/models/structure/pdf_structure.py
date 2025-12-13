"""PDF document structure."""
from dataclasses import dataclass
from typing import Dict, Any, Optional, List
from .base import BaseStructure


@dataclass
class PDFStructure(BaseStructure):
    """PDF document structure information."""
    
    total_pages: Optional[int] = None
    pdf_metadata: Optional[Dict[str, Any]] = None  # Author, title, etc.
    pdf_headings: Optional[List[Dict]] = None  # [{level: 1, text: "Heading", page: 1, start_char: 100, font_size: 16.0}]
    pdf_pages_info: Optional[List[Dict]] = None  # [{page: 1, start_char: 0, end_char: 1000}, ...]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        result = self.get_common_fields()
        result["structure_type"] = "pdf"
        
        if self.total_pages is not None:
            result["total_pages"] = self.total_pages
        if self.pdf_metadata is not None:
            result["pdf_metadata"] = self.pdf_metadata
        if self.pdf_headings is not None:
            result["pdf_headings"] = self.pdf_headings
        if self.pdf_pages_info is not None:
            result["pdf_pages_info"] = self.pdf_pages_info
        
        return result

