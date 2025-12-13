"""HTML document structure."""
from dataclasses import dataclass
from typing import Dict, Any, Optional, List
from .base import BaseStructure


@dataclass
class HTMLStructure(BaseStructure):
    """HTML document structure information."""
    
    html_title: Optional[str] = None
    html_headings: Optional[List[Dict]] = None  # [{level: 1, text: "Heading", id: "h1"}]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        result = self.get_common_fields()
        result["structure_type"] = "html"
        
        if self.html_title is not None:
            result["html_title"] = self.html_title
        if self.html_headings is not None:
            result["html_headings"] = self.html_headings
        
        return result

