"""Document structure models for different file types."""
from .base import BaseStructure
from .pdf_structure import PDFStructure
from .docx_structure import DOCXStructure
from .html_structure import HTMLStructure
from .markdown_structure import MarkdownStructure
from .factory import StructureFactory

__all__ = [
    "BaseStructure",
    "PDFStructure",
    "DOCXStructure",
    "HTMLStructure",
    "MarkdownStructure",
    "StructureFactory",
]

