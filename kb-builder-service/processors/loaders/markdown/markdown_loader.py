"""Markdown document loader."""
from pathlib import Path
import re

from ..base import BaseLoader
from models.document import Document, DocumentType
from ..utils.structure_builder import StructureBuilder
from utils.exceptions import LoaderError
from utils.logger import get_logger

logger = get_logger(__name__)


class MarkdownLoader(BaseLoader):
    """Loader for Markdown files."""
    
    def load(self, source: str, **kwargs) -> Document:
        """Load Markdown file and process images."""
        path = Path(source)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {source}")
        
        # Save source file
        original_filename = path.name
        file_id = kwargs.get("file_id") or self.file_manager.generate_file_id(original_filename)
        saved_source_path = self.file_manager.save_source_file(path, file_id, original_filename)
        
        logger.info(f"Loading Markdown file: {original_filename} (file_id: {file_id})")
        
        try:
            # Read content
            try:
                content = path.read_text(encoding='utf-8')
            except UnicodeDecodeError:
                content = path.read_text(encoding='gbk', errors='ignore')
            
            # Process images: copy local images and update paths, keep Markdown format
            content = self._process_images(content, path, file_id)
            
            # Build basic structure (headings and code blocks will be extracted in chunker)
            structure = StructureBuilder.build_markdown_structure()
            
            # Build document
            return self._build_document(
                path=path,
                content=content,
                saved_source_path=saved_source_path,
                doc_type=DocumentType.MARKDOWN,
                structure=structure,
                file_id=file_id,
                **kwargs
            )
        except Exception as e:
            logger.error(f"Failed to load Markdown file: {str(e)}", exc_info=True)
            raise LoaderError(f"Failed to load Markdown file: {str(e)}") from e
    
    def _process_images(self, content: str, path: Path, file_id: str) -> str:
        """
        Process images in Markdown content: download/copy images and update paths.
        
        Args:
            content: Markdown content
            path: Path to the Markdown file
            file_id: File ID for organizing images
        
        Returns:
            Updated Markdown content with image paths
        """
        image_counter = 0
        
        def replace_image(match):
            nonlocal image_counter
            alt_text = match.group(1)
            img_path = match.group(2)
            
            # Skip already processed images
            if img_path.startswith('/static/'):
                return match.group(0)
            
            # Handle network images: download and save
            if img_path.startswith('http://') or img_path.startswith('https://'):
                result = self.image_handler.download_image(img_path)
                if result:
                    img_data, img_ext = result
                    image_counter += 1
                    img_url = self.image_handler.save_image(img_data, file_id, image_counter, img_ext)
                    return f'![{alt_text}]({img_url})'
                return match.group(0)
            
            # Handle local images: copy to static directory
            img_path_abs = self.image_handler.resolve_image_path(img_path, path)
            if img_path_abs and img_path_abs.exists():
                with open(img_path_abs, 'rb') as f:
                    img_data = f.read()
                img_ext = img_path_abs.suffix or '.png'
                image_counter += 1
                img_url = self.image_handler.save_image(img_data, file_id, image_counter, img_ext)
                return f'![{alt_text}]({img_url})'
            
            logger.warning(f"Image file not found: {img_path}")
            return match.group(0)
        
        # Process Markdown image syntax ![alt](path)
        return re.sub(r'!\[([^\]]*)\]\(([^)]+)\)', replace_image, content)
    
    def supports(self, doc_type: DocumentType) -> bool:
        """Check if supports Markdown."""
        return doc_type == DocumentType.MARKDOWN
