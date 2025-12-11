"""PDF content extraction (text, tables, images)."""
from pathlib import Path
from typing import List, Dict, Tuple
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
        headings: List[Dict],
        pdf=None
    ) -> Tuple[str, DocumentStructure]:
        """
        Extract content from PDF and convert to Markdown.
        
        Args:
            path: Path to PDF file
            file_id: File ID for naming images
            headings: List of detected headings
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
            page_text_lengths = []  # Cache page text lengths to avoid re-extraction
            
            for page_num, page in enumerate(pdf.pages, 1):
                page_start_char = current_char_pos
                
                # Extract text
                text = page.extract_text() or ''
                page_text_lengths.append(len(text))
                
                # Extract tables
                tables = page.extract_tables()
                if tables:
                    for table_idx, table in enumerate(tables):
                        table_md = self._table_to_markdown(table)
                        table_markdown = f'\n<table index="{len(tables_info)}" page="{page_num}">\n{table_md}\n</table>\n\n'
                        markdown_parts.append(table_markdown)
                        current_char_pos += len(table_markdown)
                        tables_info.append({
                            "page": page_num,
                            "index": len(tables_info),
                            "rows": len(table),
                            "cols": len(table[0]) if table else 0
                        })
                
                if text:
                    # Wrap page content with <page> tags
                    page_start_markdown = f'<page page="{page_num}" start_char="{page_start_char}">\n\n'
                    markdown_parts.append(page_start_markdown)
                    current_char_pos += len(page_start_markdown)
                    
                    # Insert headings based on character positions
                    page_headings = [h for h in headings if h['page'] == page_num]
                    page_headings.sort(key=lambda h: h['start_char'])
                    
                    # Calculate page start offset in character stream (using cached lengths)
                    page_start_offset = sum(page_text_lengths[:page_num - 1])
                    
                    # Insert headings in reverse order to avoid position offset issues
                    text_with_headings = text
                    inserted_positions = []  # Track where we've inserted to avoid duplicates
                    
                    for heading in reversed(page_headings):
                        heading_text = heading['text']
                        heading_level = heading['level']
                        clean_heading_text = heading_text.strip()
                        heading_char_offset = heading['start_char']
                        
                        # Calculate relative position within this page
                        relative_offset = heading_char_offset - page_start_offset
                        
                        # Try to find heading at expected position first
                        found = False
                        if 0 <= relative_offset < len(text):
                            # Check if heading text appears near the expected position
                            search_start = max(0, relative_offset - 50)
                            search_end = min(len(text), relative_offset + len(clean_heading_text) + 50)
                            search_text = text[search_start:search_end]
                            
                            # Try exact match first
                            if clean_heading_text in search_text:
                                match_pos = search_text.find(clean_heading_text)
                                actual_pos = search_start + match_pos
                                
                                # Check if we haven't already inserted here
                                if not any(abs(actual_pos - pos) < 10 for pos in inserted_positions):
                                    md_heading = '#' * heading_level + ' ' + clean_heading_text + '\n\n'
                                    text_with_headings = (
                                        text_with_headings[:actual_pos] +
                                        md_heading +
                                        text_with_headings[actual_pos + len(clean_heading_text):]
                                    )
                                    inserted_positions.append(actual_pos)
                                    found = True
                        
                        # Fallback to text matching if position-based matching failed
                        if not found:
                            # Try exact match in full text
                            if clean_heading_text in text_with_headings:
                                # Find all occurrences
                                matches = list(re.finditer(re.escape(clean_heading_text), text_with_headings))
                                for match in reversed(matches):
                                    match_pos = match.start()
                                    # Check if we haven't already inserted near this position
                                    if not any(abs(match_pos - pos) < 10 for pos in inserted_positions):
                                        md_heading = '#' * heading_level + ' ' + clean_heading_text + '\n\n'
                                        text_with_headings = (
                                            text_with_headings[:match_pos] +
                                            md_heading +
                                            text_with_headings[match_pos + len(clean_heading_text):]
                                        )
                                        inserted_positions.append(match_pos)
                                        found = True
                                        break
                            
                            # Try fuzzy match as last resort
                            if not found:
                                heading_pattern = re.escape(clean_heading_text)
                                heading_pattern = heading_pattern.replace(r'\ ', r'\s+')
                                match = re.search(heading_pattern, text_with_headings, re.IGNORECASE)
                                if match:
                                    match_pos = match.start()
                                    if not any(abs(match_pos - pos) < 10 for pos in inserted_positions):
                                        md_heading = '#' * heading_level + ' ' + clean_heading_text + '\n\n'
                                        text_with_headings = (
                                            text_with_headings[:match.start()] +
                                            md_heading +
                                            text_with_headings[match.end():]
                                        )
                                        inserted_positions.append(match_pos)
                    
                    # Add page content
                    page_content = f'## Page {page_num}\n\n{text_with_headings}\n\n'
                    markdown_parts.append(page_content)
                    current_char_pos += len(page_content)
                
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
                                
                                image_counter += 1
                                img_url = self.image_handler.save_image(
                                    image_bytes, file_id, image_counter, image_ext
                                )
                                img_markdown = (
                                    f'<img src="{img_url}" alt="Page {page_num} Image {img_idx + 1}" '
                                    f'page="{page_num}" image_index="{image_counter}" />\n\n'
                                )
                                markdown_parts.append(img_markdown)
                                current_char_pos += len(img_markdown)
                            except Exception as e:
                                logger.warning(f"Failed to extract image from PDF page {page_num}: {e}")
                                continue
                    except Exception as e:
                        logger.warning(f"Failed to extract images from PDF page {page_num}: {e}")
                
                # Close page tag
                if text:
                    page_end_markdown = f'</page>\n\n'
                    markdown_parts.append(page_end_markdown)
                    page_end_char = current_char_pos
                    current_char_pos += len(page_end_markdown)
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
        
        # Build DocumentStructure
        structure = StructureBuilder.build_pdf_structure(
            total_pages=len(pages_info),
            pdf_metadata=pdf_metadata if pdf_metadata else None,
            tables=tables_info if tables_info else None,
            pdf_headings=headings if headings else None
        )
        
        return "\n".join(markdown_parts), structure
    
    def _table_to_markdown(self, table: list) -> str:
        """Convert table to Markdown format."""
        if not table or not table[0]:
            return ""
        
        md_lines = []
        # Header
        header = table[0]
        md_lines.append("| " + " | ".join(str(cell) if cell else "" for cell in header) + " |")
        md_lines.append("| " + " | ".join("---" for _ in header) + " |")
        
        # Data rows
        for row in table[1:]:
            md_lines.append("| " + " | ".join(str(cell) if cell else "" for cell in row) + " |")
        
        return "\n".join(md_lines)
