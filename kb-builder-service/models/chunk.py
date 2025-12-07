"""Chunk model."""
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List


@dataclass
class ChunkLocation:
    """Chunk location information in the source document."""
    # 通用位置
    start_char: int = 0
    end_char: int = 0
    
    # PDF 特定
    page_number: Optional[int] = None
    page_bbox: Optional[Dict[str, float]] = None  # {x0, y0, x1, y1}
    
    # DOCX 特定
    paragraph_index: Optional[int] = None
    section_index: Optional[int] = None
    
    # HTML/Markdown 特定
    heading_path: Optional[List[str]] = None  # ["H1", "H2", "H3"] 标题路径
    code_block_index: Optional[int] = None
    
    # 图片
    image_index: Optional[int] = None
    image_url: Optional[str] = None
    
    # 表格
    table_index: Optional[int] = None
    table_cell: Optional[str] = None  # "A1", "B2" 等
    
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
    location: Optional[ChunkLocation] = None  # Location information
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
    
    def get_citation(self) -> str:
        """Generate citation format for RAG."""
        parts = [f"来源: {self.document_id}"]
        
        if self.location:
            if self.location.page_number is not None:
                parts.append(f"第 {self.location.page_number} 页")
            if self.location.heading_path:
                parts.append(f"章节: {' > '.join(self.location.heading_path)}")
            if self.location.paragraph_index is not None:
                parts.append(f"段落 {self.location.paragraph_index + 1}")
        
        return ", ".join(parts)
    
    def get_source_url(self, base_url: str = "") -> str:
        """Generate source file access URL for frontend navigation."""
        if not self.file_path:
            return ""
        
        # 构建 URL，包含位置参数
        url = f"{base_url}/api/v1/sources/{self.document_id}"
        params = []
        
        if self.location:
            if self.location.page_number is not None:
                params.append(f"page={self.location.page_number}")
            if self.location.paragraph_index is not None:
                params.append(f"paragraph={self.location.paragraph_index}")
        
        if params:
            url += "?" + "&".join(params)
        
        return url
    
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
            result["location"] = self.location.to_dict()
        
        return result

