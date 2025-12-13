"""Location factory."""
from typing import Dict, Type
from models.document import DocumentType
from .base import BaseLocation
from .markdown_location import MarkdownLocation
from .pdf_location import PDFLocation


class LocationFactory:
    """Factory for creating and deserializing location objects."""
    
    _location_types: Dict[str, Type[BaseLocation]] = {
        "markdown": MarkdownLocation,
        "pdf": PDFLocation,  # PDFLocation now functionally identical to MarkdownLocation
    }
    
    @classmethod
    def create(
        cls,
        doc_type: DocumentType,
        **kwargs
    ) -> BaseLocation:
        """
        Create location object for document type.
        
        Args:
            doc_type: Document type
            **kwargs: Location fields
        
        Returns:
            Location instance
        """
        type_map = {
            DocumentType.PDF: "pdf",
            DocumentType.DOCX: "markdown",  # DOCX uses markdown location after conversion
            DocumentType.MARKDOWN: "markdown",
            DocumentType.HTML: "markdown",  # HTML uses markdown location after conversion
            DocumentType.TXT: "markdown",  # TXT uses markdown location
        }

        location_type = type_map.get(doc_type, "markdown")
        location_class = cls._location_types.get(location_type, MarkdownLocation)
        
        return location_class(**kwargs)
    
    @classmethod
    def from_dict(cls, data: Dict) -> BaseLocation:
        """
        Deserialize location object from dictionary.
        
        Args:
            data: Dictionary representation
        
        Returns:
            Location instance
        """
        location_type = data.get("location_type", "markdown")
        location_class = cls._location_types.get(location_type, MarkdownLocation)
        
        return location_class.from_dict(data)
    
    @classmethod
    def register(cls, location_type: str, location_class: Type[BaseLocation]):
        """Register a new location type."""
        cls._location_types[location_type] = location_class

