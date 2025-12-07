"""Document model."""
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List
from enum import Enum


class DocumentType(str, Enum):
    """Document types."""
    MARKDOWN = "markdown"
    PDF = "pdf"
    DOCX = "docx"
    HTML = "html"
    TXT = "txt"


@dataclass
class DocumentStructure:
    """Document structure information (type-specific)."""
    # 通用字段
    total_pages: Optional[int] = None
    total_sections: Optional[int] = None
    
    # PDF 特定
    pdf_metadata: Optional[Dict[str, Any]] = None  # 作者、标题等
    
    # DOCX 特定
    docx_styles: Optional[List[str]] = None  # 使用的样式
    docx_sections: Optional[List[Dict]] = None  # 章节信息
    
    # HTML 特定
    html_title: Optional[str] = None
    html_headings: Optional[List[Dict]] = None  # [{level: 1, text: "标题", id: "h1"}]
    
    # Markdown 特定
    md_headings: Optional[List[Dict]] = None
    md_code_blocks: Optional[List[Dict]] = None
    
    # 表格（所有类型）
    tables: Optional[List[Dict]] = None  # 表格列表
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        result = {}
        if self.total_pages is not None:
            result["total_pages"] = self.total_pages
        if self.total_sections is not None:
            result["total_sections"] = self.total_sections
        if self.pdf_metadata is not None:
            result["pdf_metadata"] = self.pdf_metadata
        if self.docx_styles is not None:
            result["docx_styles"] = self.docx_styles
        if self.docx_sections is not None:
            result["docx_sections"] = self.docx_sections
        if self.html_title is not None:
            result["html_title"] = self.html_title
        if self.html_headings is not None:
            result["html_headings"] = self.html_headings
        if self.md_headings is not None:
            result["md_headings"] = self.md_headings
        if self.md_code_blocks is not None:
            result["md_code_blocks"] = self.md_code_blocks
        if self.tables is not None:
            result["tables"] = self.tables
        return result


@dataclass
class Document:
    """Document model."""
    content: str
    source: str
    doc_type: DocumentType
    metadata: Dict[str, Any] = field(default_factory=dict)
    structure: Optional[DocumentStructure] = None  # 文档结构信息
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
    
    def get_location_info(self) -> Dict[str, Any]:
        """获取文档的位置信息（用于 RAG 引用）"""
        base_info = {
            "file": self.source,
            "type": self.doc_type.value,
            "file_path": self.metadata.get("file_path")
        }
        
        # 根据文件类型添加特定信息
        if self.structure:
            if self.doc_type == DocumentType.PDF:
                base_info["total_pages"] = self.structure.total_pages
            elif self.doc_type == DocumentType.DOCX:
                base_info["total_sections"] = self.structure.total_sections
        
        return base_info

