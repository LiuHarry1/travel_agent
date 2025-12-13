"""Markdown location model - base for all file types after Markdown conversion."""
from dataclasses import dataclass
from typing import Dict, Any
from .base import BaseLocation


@dataclass
class MarkdownLocation(BaseLocation):
    """Markdown-based location (works for all file types after conversion to Markdown)."""
    
    def __post_init__(self):
        """Initialize markdown-specific metadata if not present."""
        if "source" not in self.metadata:
            self.metadata["source"] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        result = self.get_common_fields()
        result["location_type"] = "markdown"
        # Include metadata in serialization
        result.update(self.metadata)
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MarkdownLocation":
        """Deserialize from dictionary."""
        # Extract common fields
        common = {
            "start_char": data.get("start_char", 0),
            "end_char": data.get("end_char", 0)
        }
        
        # Extract metadata (all other fields except location_type)
        metadata = {}
        for key, value in data.items():
            if key not in ["start_char", "end_char", "location_type"]:
                metadata[key] = value
        
        return cls(**common, metadata=metadata)
    
    def get_citation(self) -> str:
        """Generate citation based on markdown position."""
        parts = []
        
        # Add source if available
        source = self.metadata.get("source")
        if source:
            parts.append(f"Source: {source}")
        
        # Add character range for reference
        if self.start_char > 0 or self.end_char > 0:
            parts.append(f"chars {self.start_char}-{self.end_char}")
        
        return ", ".join(parts) if parts else "Document"
    
    def get_navigation_url(self, base_url: str, document_id: str) -> str:
        """Generate URL to markdown file with character range."""
        url = f"{base_url}/api/v1/sources/{document_id}"
        params = []
        
        # Add character range for markdown navigation
        params.append(f"start={self.start_char}")
        params.append(f"end={self.end_char}")
        
        if params:
            url += "?" + "&".join(params)
        
        return url

