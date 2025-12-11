"""PDF content extraction (text, tables, images)."""
from pathlib import Path
from typing import List, Dict, Tuple, Optional
import re

from models.document import DocumentStructure
from ..utils.image_handler import ImageHandler
from ..utils.structure_builder import StructureBuilder
from utils.exceptions import LoaderError
from utils.logger import get_logger

logger = get_logger(__name__)

# Optional imports
try:
    import pdfplumber
    HAS_PDF = True
except ImportError:
    HAS_PDF = False


class PDFExtractor:
    """Extracts content from PDF files."""
    
    def __init__(self, image_handler: ImageHandler):
        """
        Args:
            image_handler: ImageHandler instance for saving images
        """
        self.image_handler = image_handler
    
    def extract(
        self, 
        path: Path, 
        file_id: str,
        headings: Optional[List[Dict]] = None,
        pdf=None
    ) -> Tuple[str, DocumentStructure]:
        """
        Extract content from PDF and convert to Markdown.
        
        Args:
            path: Path to PDF file
            file_id: File ID for naming images
            headings: List of detected headings (deprecated, no longer used)
            pdf: Optional already-opened pdfplumber PDF object (for performance optimization)
        
        Returns:
            Tuple of (markdown_content, DocumentStructure)
        """
        if not HAS_PDF:
            raise LoaderError("pdfplumber is required for PDF files. Install with: pip install pdfplumber")
        
        markdown_parts = []
        image_counter = 0
        pages_info = []
        pdf_metadata = {}
        tables_info = []
        
        # Use provided PDF object or open new one
        should_close_pdf = pdf is None
        if pdf is None:
            pdf = pdfplumber.open(path)
        
        try:
            # Extract PDF metadata
            if pdf.metadata:
                pdf_metadata = {
                    "title": pdf.metadata.get("Title", ""),
                    "author": pdf.metadata.get("Author", ""),
                    "subject": pdf.metadata.get("Subject", ""),
                    "creator": pdf.metadata.get("Creator", ""),
                }
                logger.info(f"Extracted PDF metadata: {pdf_metadata}")
            
            # Open PyMuPDF document once for image extraction (if available)
            pdf_doc = None
            try:
                import fitz  # PyMuPDF
                pdf_doc = fitz.open(path)
            except ImportError:
                pass
            except Exception as e:
                logger.warning(f"Failed to open PDF with PyMuPDF for image extraction: {e}")
            
            # Process pages
            current_char_pos = 0
            
            for page_num, page in enumerate(pdf.pages, 1):
                page_start_char = current_char_pos
                
                # Process page: extract text, tables, and images
                page_content, page_tables, page_images, page_end_char = self._process_page(
                    page, page_num, file_id, pdf_doc, current_char_pos, image_counter
                )
                
                # Add page content to markdown parts
                if page_content:
                    markdown_parts.append(page_content)
                
                # Update counters
                current_char_pos = page_end_char
                image_counter += len(page_images)
                
                # Collect table info
                for table_info in page_tables:
                    tables_info.append(table_info)
                
                # Record page info
                pages_info.append({
                    "page": page_num,
                    "start_char": page_start_char,
                    "end_char": page_end_char,
                    "bbox": list(page.bbox) if hasattr(page, 'bbox') else None
                })
            
            # Close PyMuPDF document
            if pdf_doc:
                try:
                    pdf_doc.close()
                except Exception:
                    pass
        
        except Exception as e:
            raise LoaderError(f"Failed to process PDF: {str(e)}") from e
        finally:
            # Only close if we opened it ourselves
            if should_close_pdf and pdf:
                pdf.close()
        
        # Build DocumentStructure (headings no longer used, set to None)
        structure = StructureBuilder.build_pdf_structure(
            total_pages=len(pages_info),
            pdf_metadata=pdf_metadata if pdf_metadata else None,
            tables=tables_info if tables_info else None,
            pdf_headings=None  # No longer used
        )
        
        return "\n".join(markdown_parts), structure
    
    def _process_page(
        self,
        page,
        page_num: int,
        file_id: str,
        pdf_doc: Optional,
        start_char_pos: int,
        image_counter_start: int
    ) -> Tuple[str, List[Dict], List[str], int]:
        """
        Process a single page: extract text, tables, and images.
        
        Returns:
            (page_content_markdown, tables_info_list, image_urls_list, end_char_pos)
        """
        markdown_parts = []
        tables_info = []
        image_urls = []
        current_pos = start_char_pos
        
        # Extract tables first (before text)
        tables = page.extract_tables()
        if tables:
            for table_idx, table in enumerate(tables):
                table_md = self._table_to_markdown(table)
                table_markdown = f'\n<table index="{len(tables_info)}" page="{page_num}">\n{table_md}\n</table>\n\n'
                markdown_parts.append(table_markdown)
                current_pos += len(table_markdown)
                
                # Determine if table has header (first row looks like header)
                has_header = self._table_has_header(table)
                
                tables_info.append({
                    "page": page_num,
                    "index": len(tables_info),
                    "rows": len(table),
                    "cols": len(table[0]) if table else 0,
                    "has_header": has_header
                })
        
        # Extract text
        text = page.extract_text() or ''
        if text:
            # Wrap page content with <page> tags
            page_start_markdown = f'<page page="{page_num}" start_char="{current_pos}">\n\n'
            markdown_parts.append(page_start_markdown)
            current_pos += len(page_start_markdown)
            
            # Add page content (no heading insertion)
            page_content = f'## Page {page_num}\n\n{text}\n\n'
            markdown_parts.append(page_content)
            current_pos += len(page_content)
            
            # Close page tag
            page_end_markdown = f'</page>\n\n'
            markdown_parts.append(page_end_markdown)
            current_pos += len(page_end_markdown)
        
        # Extract images for this page (using pre-opened PyMuPDF document)
        if pdf_doc:
            try:
                page_obj = pdf_doc[page_num - 1]
                image_list = page_obj.get_images()
                
                for img_idx, img in enumerate(image_list):
                    try:
                        xref = img[0]
                        base_image = pdf_doc.extract_image(xref)
                        image_bytes = base_image["image"]
                        image_ext = f".{base_image['ext']}"
                        
                        image_counter = image_counter_start + len(image_urls) + 1
                        img_url = self.image_handler.save_image(
                            image_bytes, file_id, image_counter, image_ext
                        )
                        image_urls.append(img_url)
                        
                        img_markdown = (
                            f'<img src="{img_url}" alt="Page {page_num} Image {img_idx + 1}" '
                            f'page="{page_num}" image_index="{image_counter}" />\n\n'
                        )
                        markdown_parts.append(img_markdown)
                        current_pos += len(img_markdown)
                    except Exception as e:
                        logger.warning(f"Failed to extract image from PDF page {page_num}: {e}")
                        continue
            except Exception as e:
                logger.warning(f"Failed to extract images from PDF page {page_num}: {e}")
        
        return "\n".join(markdown_parts), tables_info, image_urls, current_pos
    
    def _table_to_markdown(self, table: list) -> str:
        """Convert table to Markdown format with improved handling."""
        if not table or not table[0]:
            return ""
        
        md_lines = []
        
        # Header
        header = table[0]
        # Escape pipe characters in cells and handle None values
        header_cells = [self._escape_table_cell(str(cell) if cell is not None else "") for cell in header]
        md_lines.append("| " + " | ".join(header_cells) + " |")
        md_lines.append("| " + " | ".join("---" for _ in header) + " |")
        
        # Data rows
        for row in table[1:]:
            # Escape pipe characters and handle None values
            row_cells = [self._escape_table_cell(str(cell) if cell is not None else "") for cell in row]
            md_lines.append("| " + " | ".join(row_cells) + " |")
        
        return "\n".join(md_lines)
    
    def _escape_table_cell(self, cell: str) -> str:
        """Escape special characters in table cells."""
        # Escape pipe characters
        cell = cell.replace("|", "\\|")
        # Replace newlines with spaces (Markdown tables don't support multi-line cells well)
        cell = cell.replace("\n", " ").replace("\r", "")
        return cell
    
    def _table_has_header(self, table: list) -> bool:
        """Determine if table has a header row."""
        if not table or len(table) < 2:
            return False
        
        # Simple heuristic: if first row has mostly non-numeric text, it's likely a header
        header_row = table[0]
        data_row = table[1] if len(table) > 1 else []
        
        if not header_row or not data_row:
            return False
        
        # Count non-empty, non-numeric cells in header
        header_text_count = sum(
            1 for cell in header_row 
            if cell and str(cell).strip() and not str(cell).strip().replace('.', '').replace('-', '').isdigit()
        )
        
        # If header has mostly text and data row has mostly numbers, likely has header
        if header_text_count >= len(header_row) * 0.7:
            return True
        
        return False
