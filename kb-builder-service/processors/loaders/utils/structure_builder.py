"""Document structure building utilities."""
from typing import Dict, Any, Optional, List
from models.document import DocumentStructure


class StructureBuilder:
    """Builds DocumentStructure objects."""
    
    @staticmethod
    def build_pdf_structure(
        total_pages: Optional[int] = None,
        pdf_metadata: Optional[Dict[str, Any]] = None,
        tables: Optional[List[Dict]] = None,
        pdf_headings: Optional[List[Dict]] = None
    ) -> DocumentStructure:
        """Build DocumentStructure for PDF."""
        return DocumentStructure(
            total_pages=total_pages,
            pdf_metadata=pdf_metadata if pdf_metadata else None,
            tables=tables if tables else None,
            pdf_headings=pdf_headings if pdf_headings else None
        )
    
    @staticmethod
    def build_docx_structure(
        total_sections: Optional[int] = None
    ) -> DocumentStructure:
        """Build DocumentStructure for DOCX."""
        return DocumentStructure(
            total_sections=total_sections
        )
    
    @staticmethod
    def build_html_structure(
        html_title: Optional[str] = None,
        html_headings: Optional[List[Dict]] = None
    ) -> DocumentStructure:
        """Build DocumentStructure for HTML."""
        return DocumentStructure(
            html_title=html_title,
            html_headings=html_headings if html_headings else None
        )
    
    @staticmethod
    def build_markdown_structure(
        md_headings: Optional[List[Dict]] = None,
        md_code_blocks: Optional[List[Dict]] = None
    ) -> DocumentStructure:
        """Build DocumentStructure for Markdown."""
        return DocumentStructure(
            md_headings=md_headings if md_headings else None,
            md_code_blocks=md_code_blocks if md_code_blocks else None
        )
    
    @staticmethod
    def build_empty_structure() -> DocumentStructure:
        """Build empty DocumentStructure."""
        return DocumentStructure()
