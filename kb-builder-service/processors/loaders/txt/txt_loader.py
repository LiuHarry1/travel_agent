"""TXT document loader."""
from pathlib import Path

from ..base import BaseLoader
from models.document import Document, DocumentType
from ..utils.structure_builder import StructureBuilder
from utils.exceptions import LoaderError
from utils.logger import get_logger

logger = get_logger(__name__)


class TXTLoader(BaseLoader):
    """Loader for plain text files."""
    
    def load(self, source: str, **kwargs) -> Document:
        """Load plain text file."""
        path = Path(source)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {source}")
        
        # Save source file
        original_filename = path.name
        file_id = kwargs.get("file_id") or self.file_manager.generate_file_id(original_filename)
        saved_source_path = self.file_manager.save_source_file(path, file_id, original_filename)
        
        logger.info(f"Loading TXT file: {original_filename} (file_id: {file_id})")
        
        try:
            # Read content
            try:
                content = path.read_text(encoding='utf-8', errors='ignore')
            except Exception:
                content = path.read_text(encoding='gbk', errors='ignore')
            
            # Build empty structure
            structure = StructureBuilder.build_empty_structure()
            
            # Build document
            return self._build_document(
                path=path,
                content=content,
                saved_source_path=saved_source_path,
                doc_type=DocumentType.TXT,
                structure=structure,
                file_id=file_id,
                **kwargs
            )
        except Exception as e:
            logger.error(f"Failed to load TXT file: {str(e)}", exc_info=True)
            raise LoaderError(f"Failed to load TXT file: {str(e)}") from e
    
    def supports(self, doc_type: DocumentType) -> bool:
        """Check if supports TXT."""
        return doc_type == DocumentType.TXT
