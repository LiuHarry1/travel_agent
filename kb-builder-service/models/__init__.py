"""Data models."""
from .document import Document, DocumentType, DocumentStructure
from .chunk import Chunk, ChunkLocation
from .structure import (
    BaseStructure,
    PDFStructure,
    DOCXStructure,
    HTMLStructure,
    MarkdownStructure,
    StructureFactory,
)

__all__ = [
    "Document",
    "DocumentType",
    "DocumentStructure",  # Type alias for Union of all structure types
    "Chunk",
    "ChunkLocation",  # Legacy, should migrate to BaseLocation
    "BaseStructure",
    "PDFStructure",
    "DOCXStructure",
    "HTMLStructure",
    "MarkdownStructure",
    "StructureFactory",
]

