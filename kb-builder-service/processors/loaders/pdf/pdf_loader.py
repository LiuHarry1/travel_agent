"""PDF document loader."""
from pathlib import Path
from typing import Optional
import time

from ..base import BaseLoader
from models.document import Document, DocumentType
from utils.exceptions import LoaderError
from utils.logger import get_logger
from .pdf_extractor import PDFExtractor

logger = get_logger(__name__)

# Optional imports
try:
    import pdfplumber
    HAS_PDF = True
except ImportError:
    HAS_PDF = False


class PDFLoader(BaseLoader):
    """Loader for PDF files."""
    
    def __init__(self, static_dir: str = "static", base_url: str = ""):
        """
        Args:
            static_dir: Static files root directory
            base_url: Base URL for static files
        """
        super().__init__(static_dir, base_url)
        self.pdf_extractor = PDFExtractor(self.image_handler)
    
    def load(self, source: str, **kwargs) -> Document:
        """Load PDF file and convert to Markdown."""
        if not HAS_PDF:
            raise LoaderError("pdfplumber is required for PDF files. Install with: pip install pdfplumber")
        
        path = Path(source)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {source}")
        
        # Save source file
        original_filename = path.name
        file_id = kwargs.get("file_id") or self.file_manager.generate_file_id(original_filename)
        saved_source_path = self.file_manager.save_source_file(path, file_id, original_filename)
        
        logger.info(f"Loading PDF file: {original_filename} (file_id: {file_id})")
        
        start_time = time.time()
        pdf = None
        
        try:
            # Open PDF once and use it for content extraction
            pdf = pdfplumber.open(path)
            
            # Log PDF info
            num_pages = len(pdf.pages)
            logger.info(f"PDF has {num_pages} pages")
            
            # Extract content
            content, structure = self.pdf_extractor.extract(path, file_id, headings=None, pdf=pdf)
            
            # Log processing stats
            processing_time = time.time() - start_time
            logger.info(
                f"Successfully processed PDF: {original_filename} "
                f"({num_pages} pages, {processing_time:.2f}s)"
            )
            
            # Build document
            return self._build_document(
                path=path,
                content=content,
                saved_source_path=saved_source_path,
                doc_type=DocumentType.PDF,
                structure=structure,
                file_id=file_id,
                **kwargs
            )
        except FileNotFoundError as e:
            logger.error(f"PDF file not found: {source}")
            raise
        except Exception as e:
            logger.error(
                f"Failed to load PDF file {source}: {str(e)}",
                exc_info=True
            )
            raise LoaderError(f"Failed to load PDF file: {str(e)}") from e
        finally:
            # Ensure PDF is closed
            if pdf:
                try:
                    pdf.close()
                except Exception as close_error:
                    logger.warning(f"Error closing PDF file: {close_error}")
    
    def supports(self, doc_type: DocumentType) -> bool:
        """Check if supports PDF."""
        return doc_type == DocumentType.PDF
