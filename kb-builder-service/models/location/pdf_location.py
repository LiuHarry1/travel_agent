"""PDF location model - extends MarkdownLocation (for backward compatibility)."""
from dataclasses import dataclass
from typing import Dict, Any
from .markdown_location import MarkdownLocation


@dataclass
class PDFLocation(MarkdownLocation):
    """
    PDF-specific location information.
    
    Note: In unified Markdown architecture, this is functionally identical to MarkdownLocation.
    Kept for backward compatibility. All PDF-specific fields (page_number, table_index, etc.)
    are no longer needed as everything is tracked by character position in Markdown.
    """
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        # Use parent's to_dict and override location_type
        result = super().to_dict()
        result["location_type"] = "pdf"  # Override to "pdf" for backward compatibility
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PDFLocation":
        """Deserialize from dictionary."""
        # Use parent's from_dict logic
        return super().from_dict(data)
    
    # get_citation 和 get_navigation_url 直接使用父类的实现
    # 不需要覆盖，因为功能完全一样
