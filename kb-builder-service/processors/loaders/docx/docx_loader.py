"""DOCX document loader."""
from pathlib import Path
import time

try:
    from docx import Document as DocxDocument
except ImportError:
    DocxDocument = None

from ..base import BaseLoader
from models.document import Document, DocumentType
from models.structure import DOCXStructure
from ..utils.structure_builder import StructureBuilder
from utils.exceptions import LoaderError
from utils.logger import get_logger

logger = get_logger(__name__)


class DOCXLoader(BaseLoader):
    """Loader for DOCX files."""
    
    def __init__(self, static_dir: str = "static", base_url: str = ""):
        """
        Args:
            static_dir: Static files root directory
            base_url: Base URL for static files
        """
        super().__init__(static_dir, base_url)
        
        if DocxDocument is None:
            logger.warning(
                "python-docx not installed. DOCX loading will not work. "
                "Install with: pip install python-docx"
            )
    
    def load(self, source: str, **kwargs) -> Document:
        """Load DOCX file and convert to Markdown."""
        if DocxDocument is None:
            raise ImportError(
                "python-docx is required for DOCX files. "
                "Install with: pip install python-docx"
            )
        
        path = Path(source)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {source}")
        
        # Save source file
        original_filename = path.name
        file_id = kwargs.get("file_id") or self.file_manager.generate_file_id(original_filename)
        saved_source_path = self.file_manager.save_source_file(path, file_id, original_filename)
        
        logger.info(f"Loading DOCX file: {original_filename} (file_id: {file_id})")
        
        start_time = time.time()
        
        try:
            # Extract content and convert to Markdown
            content, structure = self._extract_docx(path)
            
            # Log processing stats
            processing_time = time.time() - start_time
            logger.info(
                f"Successfully processed DOCX: {original_filename} "
                f"({processing_time:.2f}s)"
            )
            
            # Build document
            return self._build_document(
                path=path,
                content=content,
                saved_source_path=saved_source_path,
                doc_type=DocumentType.DOCX,
                structure=structure,
                file_id=file_id,
                **kwargs
            )
        except FileNotFoundError as e:
            logger.error(f"DOCX file not found: {source}")
            raise
        except Exception as e:
            logger.error(
                f"Failed to load DOCX file {source}: {str(e)}",
                exc_info=True
            )
            raise LoaderError(f"Failed to load DOCX file: {str(e)}") from e
    
    def _extract_docx(self, path: Path) -> tuple[str, DOCXStructure]:
        """
        Extract content from DOCX and convert to Markdown.
        
        Args:
            path: Path to DOCX file
        
        Returns:
            Tuple of (markdown_content, DOCXStructure)
        """
        try:
            doc = DocxDocument(str(path))
            
            # Convert paragraphs to Markdown
            markdown_parts = []
            for paragraph in doc.paragraphs:
                text = paragraph.text.strip()
                if not text:
                    continue
                
                # Check if it's a heading
                if paragraph.style.name.startswith('Heading'):
                    level = int(paragraph.style.name.split()[-1]) if paragraph.style.name.split()[-1].isdigit() else 1
                    level = min(level, 6)  # Max heading level is 6
                    markdown_parts.append(f"{'#' * level} {text}\n\n")
                else:
                    markdown_parts.append(f"{text}\n\n")
            
            # Convert tables to Markdown
            for table in doc.tables:
                markdown_parts.append("\n")
                for row in table.rows:
                    cells = [cell.text.strip() for cell in row.cells]
                    markdown_parts.append("| " + " | ".join(cells) + " |\n")
                markdown_parts.append("\n")
            
            full_markdown = "".join(markdown_parts)
            
            # Build DOCXStructure
            structure = StructureBuilder.build_docx_structure()
            
            logger.info(f"Successfully extracted DOCX content")
            
            return full_markdown, structure
                
        except Exception as e:
            logger.error(f"Failed to extract DOCX content: {str(e)}", exc_info=True)
            raise LoaderError(f"Failed to process DOCX: {str(e)}") from e
    
    def supports(self, doc_type: DocumentType) -> bool:
        """Check if supports DOCX."""
        return doc_type == DocumentType.DOCX

