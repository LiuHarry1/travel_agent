"""HTML document loader."""
from pathlib import Path
from urllib.parse import urlparse

from ..base import BaseLoader
from models.document import Document, DocumentType
from ..utils.structure_builder import StructureBuilder
from utils.exceptions import LoaderError
from utils.logger import get_logger

logger = get_logger(__name__)

# Optional imports
try:
    from bs4 import BeautifulSoup
    HAS_HTML = True
except ImportError:
    HAS_HTML = False

try:
    import markdownify
    HAS_MARKDOWNIFY = True
except ImportError:
    HAS_MARKDOWNIFY = False


class HTMLLoader(BaseLoader):
    """Loader for HTML files."""
    
    def load(self, source: str, **kwargs) -> Document:
        """Load HTML file and convert to Markdown."""
        if not HAS_HTML:
            raise LoaderError("beautifulsoup4 is required for HTML files. Install with: pip install beautifulsoup4")
        
        path = Path(source)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {source}")
        
        # Save source file
        original_filename = path.name
        file_id = kwargs.get("file_id") or self.file_manager.generate_file_id(original_filename)
        saved_source_path = self.file_manager.save_source_file(path, file_id, original_filename)
        
        logger.info(f"Loading HTML file: {original_filename} (file_id: {file_id})")
        
        try:
            # Read HTML content
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    html_content = f.read()
            except UnicodeDecodeError:
                with open(path, 'r', encoding='gbk', errors='ignore') as f:
                    html_content = f.read()
            
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Extract and save images
            image_counter = 0
            for img_tag in soup.find_all('img'):
                src = img_tag.get('src', '')
                if not src:
                    continue
                
                try:
                    # Handle network images
                    if src.startswith('http://') or src.startswith('https://'):
                        result = self.image_handler.download_image(src)
                        if result:
                            img_data, img_ext = result
                            image_counter += 1
                            img_url = self.image_handler.save_image(
                                img_data, file_id, image_counter, img_ext
                            )
                            alt_text = img_tag.get('alt', f'Image {image_counter}')
                            img_tag.replace_with(f'<img src="{img_url}" alt="{alt_text}" />')
                        continue
                    
                    # Handle local images
                    img_path_abs = self.image_handler.resolve_image_path(src, path)
                    if img_path_abs:
                        with open(img_path_abs, 'rb') as f:
                            img_data = f.read()
                        img_ext = img_path_abs.suffix or '.png'
                        
                        image_counter += 1
                        img_url = self.image_handler.save_image(
                            img_data, file_id, image_counter, img_ext
                        )
                        alt_text = img_tag.get('alt', f'Image {image_counter}')
                        img_tag.replace_with(f'<img src="{img_url}" alt="{alt_text}" />')
                    else:
                        logger.warning(f"Image file not found: {src}")
                except Exception as e:
                    logger.warning(f"Failed to process image {src}: {e}")
                    continue
            
            # Extract heading information
            headings = []
            for heading in soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6']):
                level = int(heading.name[1])
                headings.append({
                    "level": level,
                    "text": heading.get_text().strip(),
                    "id": heading.get('id', '')
                })
            
            # Convert to Markdown
            if HAS_MARKDOWNIFY:
                markdown = markdownify.markdownify(str(soup), heading_style="ATX")
            else:
                markdown = soup.get_text()
                logger.warning("markdownify not available, using simple text extraction")
            
            # Build structure
            structure = StructureBuilder.build_html_structure(
                html_title=soup.title.string if soup.title else None,
                html_headings=headings if headings else None
            )
            
            # Build document
            return self._build_document(
                path=path,
                content=markdown,
                saved_source_path=saved_source_path,
                doc_type=DocumentType.HTML,
                structure=structure,
                file_id=file_id,
                **kwargs
            )
        except Exception as e:
            logger.error(f"Failed to load HTML file: {str(e)}", exc_info=True)
            raise LoaderError(f"Failed to load HTML file: {str(e)}") from e
    
    def supports(self, doc_type: DocumentType) -> bool:
        """Check if supports HTML."""
        return doc_type == DocumentType.HTML
