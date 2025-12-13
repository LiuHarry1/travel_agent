"""Markdown document structure."""
from dataclasses import dataclass
from typing import Dict, Any, Optional, List
from .base import BaseStructure


@dataclass
class MarkdownStructure(BaseStructure):
    """Markdown document structure information."""
    
    md_headings: Optional[List[Dict]] = None
    md_code_blocks: Optional[List[Dict]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        result = self.get_common_fields()
        result["structure_type"] = "markdown"
        
        if self.md_headings is not None:
            result["md_headings"] = self.md_headings
        if self.md_code_blocks is not None:
            result["md_code_blocks"] = self.md_code_blocks
        
        return result

