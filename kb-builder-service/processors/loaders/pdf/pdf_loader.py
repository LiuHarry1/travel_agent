"""PDF document loader."""
from pathlib import Path
import time
import re

import pymupdf4llm

from ..base import BaseLoader
from models.document import Document, DocumentType
from models.structure import PDFStructure
from ..utils.structure_builder import StructureBuilder
from utils.exceptions import LoaderError
from utils.logger import get_logger

logger = get_logger(__name__)


class PDFLoader(BaseLoader):
    """Loader for PDF files."""
    
    def __init__(self, static_dir: str = "static", base_url: str = ""):
        """
        Args:
            static_dir: Static files root directory
            base_url: Base URL for static files
        """
        super().__init__(static_dir, base_url)
    
    def load(self, source: str, **kwargs) -> Document:
        """Load PDF file and convert to Markdown using pymupdf4llm."""
        path = Path(source)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {source}")
        
        # Save source file
        original_filename = path.name
        file_id = kwargs.get("file_id") or self.file_manager.generate_file_id(original_filename)
        saved_source_path = self.file_manager.save_source_file(path, file_id, original_filename)
        
        logger.info(f"Loading PDF file: {original_filename} (file_id: {file_id})")
        
        start_time = time.time()
        
        try:
            # Extract content using pymupdf4llm
            content, structure = self._extract_pdf(path, file_id)
            
            # Save markdown file
            saved_markdown_path = self.file_manager.save_markdown_file(
                markdown_content=content,
                file_id=file_id,
                original_filename=original_filename
            )
            logger.info(f"Saved markdown file to: {saved_markdown_path}")
            
            # Calculate relative path from static_dir for storage
            # This makes it easier to resolve later
            static_dir = self.file_manager.static_dir
            try:
                markdown_file_path_relative = saved_markdown_path.relative_to(static_dir)
            except ValueError:
                # If not relative, use absolute path
                markdown_file_path_relative = saved_markdown_path
            
            # Log processing stats
            processing_time = time.time() - start_time
            logger.info(
                f"Successfully processed PDF: {original_filename} "
                f"({processing_time:.2f}s)"
            )
            
            # Build document with markdown file path in metadata
            return self._build_document(
                path=path,
                content=content,
                saved_source_path=saved_source_path,
                doc_type=DocumentType.PDF,
                structure=structure,
                file_id=file_id,
                markdown_file_path=str(markdown_file_path_relative),
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
    
    def _extract_pdf(self, path: Path, file_id: str) -> tuple[str, PDFStructure]:
        """
        Extract content from PDF and convert to Markdown using pymupdf4llm.
        
        Args:
            path: Path to PDF file
            file_id: File ID for naming images
        
        Returns:
            Tuple of (markdown_content, PDFStructure)
        """
        try:
            # 1. Prepare image directory for pymupdf4llm
            # pymupdf4llm will save images here
            image_dir = self.image_handler.images_dir / file_id
            image_dir.mkdir(parents=True, exist_ok=True)
            
            # 2. Extract PDF using pymupdf4llm with automatic image saving
            logger.info(f"Extracting PDF content using pymupdf4llm: {path}")
            logger.info(f"Images will be saved to: {image_dir}")
            
            # Get full Markdown (not page-by-page)
            full_markdown = pymupdf4llm.to_markdown(
                str(path),
                page_chunks=False,  # Get full document as single Markdown string
                write_images=True,  # Let pymupdf4llm save images automatically
                image_path=str(image_dir),  # Where to save images
                image_format="png"  # Image format
            )
            
            if not full_markdown or not full_markdown.strip():
                raise LoaderError(f"No content extracted from PDF: {path}")
            
            # 3. Update image paths in Markdown to include hostname
            updated_markdown = self._update_image_paths(
                full_markdown, 
                file_id, 
                self.image_handler.base_url
            )
            
            # 4. Build PDFStructure (simplified - no metadata needed)
            structure = StructureBuilder.build_pdf_structure()
            
            logger.info(f"Successfully extracted PDF using pymupdf4llm")
            
            return updated_markdown, structure
                
        except Exception as e:
            logger.error(f"Failed to extract PDF content: {str(e)}", exc_info=True)
            raise LoaderError(f"Failed to process PDF: {str(e)}") from e
    
    def _update_image_paths(
        self, 
        text: str, 
        file_id: str, 
        base_url: str
    ) -> str:
        """
        Update image paths in Markdown to include hostname.
        
        pymupdf4llm saves images and references them in Markdown like:
        ![](image.png) or ![](path/to/image.png) or ![](./image.png)
        
        We need to update to:
        ![]({base_url}/static/images/{file_id}/image.png)
        
        Args:
            text: Markdown text with image references
            file_id: File ID for the PDF
            base_url: Base URL for static files
        
        Returns:
            Updated Markdown text with full image URLs
        """
        # Pattern to match Markdown image syntax: ![](path) or ![alt](path)
        image_pattern = re.compile(
            r'!\[([^\]]*)\]\(([^)]+)\)',
            re.MULTILINE
        )
        
        def replace_image_path(match):
            alt_text = match.group(1)
            img_path = match.group(2)
            
            # If already a full URL, keep it
            if img_path.startswith('http://') or img_path.startswith('https://'):
                return match.group(0)
            
            # Extract filename from path
            # Handle relative paths like ./image.png, ../image.png, or just image.png
            img_path_clean = img_path.lstrip('./').lstrip('../')
            img_filename = Path(img_path_clean).name
            
            # Build new URL with hostname
            if base_url:
                # Full URL with hostname
                new_url = f"{base_url}/static/images/{file_id}/{img_filename}"
            else:
                # Relative path (fallback)
                new_url = f"/static/images/{file_id}/{img_filename}"
            
            return f'![{alt_text}]({new_url})'
        
        updated_text = image_pattern.sub(replace_image_path, text)
        return updated_text
    
    def supports(self, doc_type: DocumentType) -> bool:
        """Check if supports PDF."""
        return doc_type == DocumentType.PDF
