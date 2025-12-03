"""Document model."""
from dataclasses import dataclass
from typing import Dict, Any
from enum import Enum


class DocumentType(str, Enum):
    """Document types."""
    MARKDOWN = "markdown"
    PDF = "pdf"
    DOCX = "docx"
    HTML = "html"
    TXT = "txt"


@dataclass
class Document:
    """Document model."""
    content: str
    source: str
    doc_type: DocumentType
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}

