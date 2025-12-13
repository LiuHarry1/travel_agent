"""Factory for creating and deserializing structure objects."""
from typing import Dict, Type, Any, Union, TYPE_CHECKING
from .base import BaseStructure
from .pdf_structure import PDFStructure
from .docx_structure import DOCXStructure
from .html_structure import HTMLStructure
from .markdown_structure import MarkdownStructure

if TYPE_CHECKING:
    from models.document import DocumentType


class StructureFactory:
    """Factory for creating and deserializing structure objects."""

    _structure_types: Dict[str, Type[BaseStructure]] = {
        "pdf": PDFStructure,
        "docx": DOCXStructure,
        "html": HTMLStructure,
        "markdown": MarkdownStructure,
    }

    @classmethod
    def create(
        cls,
        doc_type: "DocumentType",
        **kwargs
    ) -> BaseStructure:
        """
        Create structure object for document type.

        Args:
            doc_type: Document type
            **kwargs: Structure fields

        Returns:
            Structure instance
        """
        # Import here to avoid circular import
        from models.document import DocumentType
        
        type_map = {
            DocumentType.PDF: "pdf",
            DocumentType.DOCX: "docx",
            DocumentType.HTML: "html",
            DocumentType.MARKDOWN: "markdown",
            DocumentType.TXT: "markdown",  # TXT uses markdown structure
        }

        structure_type = type_map.get(doc_type, "markdown")
        structure_class = cls._structure_types.get(structure_type)
        if not structure_class:
            raise ValueError(f"No structure class registered for type: {structure_type}")

        return structure_class(**kwargs)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> BaseStructure:
        """
        Deserialize structure object from dictionary.

        Args:
            data: Dictionary representation
        Returns:
            Structure instance
        """
        structure_type = data.get("structure_type")
        if not structure_type:
            raise ValueError("Missing 'structure_type' in structure data for deserialization.")

        structure_class = cls._structure_types.get(structure_type)
        if not structure_class:
            raise ValueError(f"No structure class registered for type: {structure_type}")

        # Remove structure_type from data before creating instance
        data_copy = {k: v for k, v in data.items() if k != "structure_type"}
        return structure_class(**data_copy)

    @classmethod
    def register(cls, structure_type: str, structure_class: Type[BaseStructure]):
        """Register a new structure type."""
        cls._structure_types[structure_type] = structure_class

