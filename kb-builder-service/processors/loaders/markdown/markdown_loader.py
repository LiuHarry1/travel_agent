"""Markdown document loader."""
from pathlib import Path
import re
from urllib.parse import urlparse

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
            
            image_counter = 0
            
            # Process Markdown image syntax ![alt](path)
            def replace_markdown_image(match):
                nonlocal image_counter
                alt_text = match.group(1)
                img_path = match.group(2)
                
                # Handle network images
                if img_path.startswith('http://') or img_path.startswith('https://'):
                    result = self.image_handler.download_image(img_path)
                    if result:
                        img_data, img_ext = result
                        image_counter += 1
                        img_url = self.image_handler.save_image(
                            img_data, file_id, image_counter, img_ext
                        )
                        return f'<img src="{img_url}" alt="{alt_text}" />'
                    return match.group(0)
                
                # Handle local images
                img_path_abs = self.image_handler.resolve_image_path(img_path, path)
                if img_path_abs:
                    with open(img_path_abs, 'rb') as f:
                        img_data = f.read()
                    img_ext = img_path_abs.suffix or '.png'
                    
                    image_counter += 1
                    img_url = self.image_handler.save_image(
                        img_data, file_id, image_counter, img_ext
                    )
                    return f'<img src="{img_url}" alt="{alt_text}" />'
                
                logger.warning(f"Image file not found: {img_path}")
                return match.group(0)
            
            # Replace Markdown image syntax
            content = re.sub(r'!\[([^\]]*)\]\(([^)]+)\)', replace_markdown_image, content)
            
            # Process HTML img tags with relative paths
            def replace_html_image(match):
                nonlocal image_counter
                img_tag = match.group(0)
                src_match = re.search(r'src=["\']([^"\']+)["\']', img_tag)
                if not src_match:
                    return img_tag
                
                src = src_match.group(1)
                
                # Skip network images or already absolute paths
                if src.startswith('http://') or src.startswith('https://') or src.startswith('/static/'):
                    return img_tag
                
                # Handle local relative paths
                img_path_abs = self.image_handler.resolve_image_path(src, path)
                if img_path_abs:
                    with open(img_path_abs, 'rb') as f:
                        img_data = f.read()
                    img_ext = img_path_abs.suffix or '.png'
                    
                    image_counter += 1
                    img_url = self.image_handler.save_image(
                        img_data, file_id, image_counter, img_ext
                    )
                    return re.sub(r'src=["\'][^"\']+["\']', f'src="{img_url}"', img_tag)
                
                return img_tag
            
            # Replace HTML img tags
            content = re.sub(r'<img[^>]+>', replace_html_image, content)
            
            # Extract headings and code blocks
            headings = []
            code_blocks = []
            
            # Extract Markdown headings
            heading_pattern = r'^(#{1,6})\s+(.+)$'
            for match in re.finditer(heading_pattern, content, re.MULTILINE):
                level = len(match.group(1))
                text = match.group(2).strip()
                headings.append({"level": level, "text": text})
            
            # Extract code blocks
            code_block_pattern = r'```(\w+)?\n(.*?)```'
            for idx, match in enumerate(re.finditer(code_block_pattern, content, re.DOTALL)):
                lang = match.group(1) or ""
                code_blocks.append({
                    "index": idx,
                    "language": lang,
                    "length": len(match.group(2))
                })
            
            # Build structure
            structure = StructureBuilder.build_markdown_structure(
                md_headings=headings if headings else None,
                md_code_blocks=code_blocks if code_blocks else None
            )
            
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
    
    def supports(self, doc_type: DocumentType) -> bool:
        """Check if supports Markdown."""
        return doc_type == DocumentType.MARKDOWN
