"""Document structure building utilities."""
from typing import Dict, Any, Optional, List
from models.structure import (
    PDFStructure,
    DOCXStructure,
    HTMLStructure,
    MarkdownStructure,
    BaseStructure,
)


class StructureBuilder:
    """Builds document structure objects."""
    
    @staticmethod
    def build_pdf_structure(
        pdf_metadata: Optional[Dict[str, Any]] = None
    ) -> PDFStructure:
        """Build PDFStructure for PDF (simplified - no page-level info needed)."""
        return PDFStructure(
            pdf_metadata=pdf_metadata if pdf_metadata else None
        )
    
    @staticmethod
    def build_docx_structure(
        total_sections: Optional[int] = None,
        docx_styles: Optional[List[str]] = None,
        docx_sections: Optional[List[Dict]] = None,
        tables: Optional[List[Dict]] = None
    ) -> DOCXStructure:
        """Build DOCXStructure for DOCX."""
        return DOCXStructure(
            total_sections=total_sections,
            docx_styles=docx_styles if docx_styles else None,
            docx_sections=docx_sections if docx_sections else None,
            tables=tables if tables else None
        )
    
    @staticmethod
    def build_html_structure(
        html_title: Optional[str] = None,
        html_headings: Optional[List[Dict]] = None,
        tables: Optional[List[Dict]] = None
    ) -> HTMLStructure:
        """Build HTMLStructure for HTML."""
        return HTMLStructure(
            html_title=html_title,
            html_headings=html_headings if html_headings else None,
            tables=tables if tables else None
        )
    
    @staticmethod
    def build_markdown_structure(
        md_headings: Optional[List[Dict]] = None,
        md_code_blocks: Optional[List[Dict]] = None,
        tables: Optional[List[Dict]] = None
    ) -> MarkdownStructure:
        """Build MarkdownStructure for Markdown."""
        return MarkdownStructure(
            md_headings=md_headings if md_headings else None,
            md_code_blocks=md_code_blocks if md_code_blocks else None,
            tables=tables if tables else None
        )
