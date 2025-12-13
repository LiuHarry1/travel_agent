"""Chunk model."""
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List, Union
from models.location.base import BaseLocation
from models.location.factory import LocationFactory


@dataclass
class ChunkLocation:
    """Chunk location information in the source document."""
    # Common location
    start_char: int = 0
    end_char: int = 0
    
    # PDF specific
    page_number: Optional[int] = None
    page_bbox: Optional[Dict[str, float]] = None  # {x0, y0, x1, y1}
    
    # DOCX specific
    paragraph_index: Optional[int] = None
    section_index: Optional[int] = None
    
    # HTML/Markdown specific
    heading_path: Optional[List[str]] = None  # ["H1", "H2", "H3"] heading path
    code_block_index: Optional[int] = None
    
    # Images
    image_index: Optional[int] = None
    image_url: Optional[str] = None
    
    # Tables
    table_index: Optional[int] = None
    table_cell: Optional[str] = None  # "A1", "B2", etc.
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        result = {}
        if self.start_char is not None:
            result["start_char"] = self.start_char
        if self.end_char is not None:
            result["end_char"] = self.end_char
        if self.page_number is not None:
            result["page_number"] = self.page_number
        if self.page_bbox is not None:
            result["page_bbox"] = self.page_bbox
        if self.paragraph_index is not None:
            result["paragraph_index"] = self.paragraph_index
        if self.section_index is not None:
            result["section_index"] = self.section_index
        if self.heading_path is not None:
            result["heading_path"] = self.heading_path
        if self.code_block_index is not None:
            result["code_block_index"] = self.code_block_index
        if self.image_index is not None:
            result["image_index"] = self.image_index
        if self.image_url is not None:
            result["image_url"] = self.image_url
        if self.table_index is not None:
            result["table_index"] = self.table_index
        if self.table_cell is not None:
            result["table_cell"] = self.table_cell
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ChunkLocation":
        """Create from dictionary."""
        return cls(**data)


@dataclass
class Chunk:
    """Text chunk model."""
    text: str
    chunk_id: str
    document_id: str  # Original filename for display
    chunk_index: int
    metadata: Dict[str, Any] = field(default_factory=dict)
    embedding: Optional[list] = None
    file_path: Optional[str] = None  # Actual file path for accessing the file
    location: Optional[Union[BaseLocation, 'ChunkLocation']] = None  # Location information (supports both old and new)
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
    
    def get_citation(self) -> str:
        """Generate citation format for RAG."""
        if self.location:
            # Use location's get_citation method if available (new system)
            if isinstance(self.location, BaseLocation):
                return self.location.get_citation()
            # Fallback to old ChunkLocation format
            parts = [f"Source: {self.document_id}"]
            if hasattr(self.location, 'page_number') and self.location.page_number is not None:
                parts.append(f"Page {self.location.page_number}")
            if hasattr(self.location, 'heading_path') and self.location.heading_path:
                parts.append(f"Section: {' > '.join(self.location.heading_path)}")
            if hasattr(self.location, 'paragraph_index') and self.location.paragraph_index is not None:
                parts.append(f"Paragraph {self.location.paragraph_index + 1}")
            return ", ".join(parts)
        
        return f"Source: {self.document_id}"
    
    def get_source_url(self, base_url: str = "") -> str:
        """Generate source file access URL for frontend navigation."""
        if not self.file_path:
            return ""
        
        if self.location:
            # Use location's get_navigation_url method if available (new system)
            if isinstance(self.location, BaseLocation):
                return self.location.get_navigation_url(base_url, self.document_id)
            # Fallback to old ChunkLocation format
            url = f"{base_url}/api/v1/sources/{self.document_id}"
            params = []
            if hasattr(self.location, 'page_number') and self.location.page_number is not None:
                params.append(f"page={self.location.page_number}")
            if hasattr(self.location, 'paragraph_index') and self.location.paragraph_index is not None:
                params.append(f"paragraph={self.location.paragraph_index}")
            if params:
                url += "?" + "&".join(params)
            return url
        
        return f"{base_url}/api/v1/sources/{self.document_id}"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization (e.g., for Milvus storage)."""
        result = {
            "text": self.text,
            "chunk_id": self.chunk_id,
            "document_id": self.document_id,
            "chunk_index": self.chunk_index,
            "metadata": self.metadata,
            "file_path": self.file_path or "",
        }
        
        if self.location:
            # Use location's to_dict method
            if isinstance(self.location, BaseLocation):
                result["location"] = self.location.to_dict()
            elif hasattr(self.location, 'to_dict'):
                result["location"] = self.location.to_dict()
            else:
                # Fallback: convert to dict manually
                result["location"] = {
                    "start_char": getattr(self.location, 'start_char', 0),
                    "end_char": getattr(self.location, 'end_char', 0),
                }
                if hasattr(self.location, 'page_number') and self.location.page_number is not None:
                    result["location"]["page_number"] = self.location.page_number
        
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Chunk":
        """Create Chunk from dictionary."""
        location = None
        if data.get("location"):
            try:
                # Try to deserialize using LocationFactory (new system)
                location = LocationFactory.from_dict(data["location"])
            except Exception:
                # Fallback to old ChunkLocation
                try:
                    location = ChunkLocation.from_dict(data["location"])
                except Exception:
                    pass
        
        return cls(
            text=data["text"],
            chunk_id=data["chunk_id"],
            document_id=data["document_id"],
            chunk_index=data["chunk_index"],
            metadata=data.get("metadata", {}),
            file_path=data.get("file_path"),
            location=location
        )

