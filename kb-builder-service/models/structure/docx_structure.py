"""DOCX document structure."""
from dataclasses import dataclass
from typing import Dict, Any, Optional, List
from .base import BaseStructure


@dataclass
class DOCXStructure(BaseStructure):
    """DOCX document structure information."""
    
    total_sections: Optional[int] = None
    docx_styles: Optional[List[str]] = None  # Used styles
    docx_sections: Optional[List[Dict]] = None  # Section information
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        result = self.get_common_fields()
        result["structure_type"] = "docx"
        
        if self.total_sections is not None:
            result["total_sections"] = self.total_sections
        if self.docx_styles is not None:
            result["docx_styles"] = self.docx_styles
        if self.docx_sections is not None:
            result["docx_sections"] = self.docx_sections
        
        return result

