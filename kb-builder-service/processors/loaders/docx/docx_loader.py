"""DOCX document loader."""
from pathlib import Path
import zipfile
import io

from ..base import BaseLoader
from models.document import Document, DocumentType
from ..utils.structure_builder import StructureBuilder
from utils.exceptions import LoaderError
from utils.logger import get_logger

logger = get_logger(__name__)

# Optional imports
try:
    from docx import Document as DocxDocument
    HAS_DOCX = True
except ImportError:
    HAS_DOCX = False

try:
    from PIL import Image
    HAS_PIL = True
except ImportError:
    HAS_PIL = False


class DOCXLoader(BaseLoader):
    """Loader for DOCX files."""
    
    def load(self, source: str, **kwargs) -> Document:
        """Load DOCX file and convert to Markdown."""
        if not HAS_DOCX:
            raise LoaderError("python-docx is required for DOCX files. Install with: pip install python-docx")
        
        path = Path(source)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {source}")
        
        # Save source file
        original_filename = path.name
        file_id = kwargs.get("file_id") or self.file_manager.generate_file_id(original_filename)
        saved_source_path = self.file_manager.save_source_file(path, file_id, original_filename)
        
        logger.info(f"Loading DOCX file: {original_filename} (file_id: {file_id})")
        
        try:
            doc = DocxDocument(path)
            markdown_parts = []
            image_counter = 0
            
            # Process paragraphs
            for para in doc.paragraphs:
                if para.text.strip():
                    markdown_parts.append(para.text)
            
            # Extract images
            try:
                with zipfile.ZipFile(path, 'r') as docx_zip:
                    image_files = [f for f in docx_zip.namelist() 
                                  if f.startswith('word/media/')]
                    
                    for img_file in image_files:
                        try:
                            image_counter += 1
                            img_data = docx_zip.read(img_file)
                            
                            # Determine image extension
                            img_ext = Path(img_file).suffix
                            if not img_ext:
                                if HAS_PIL:
                                    try:
                                        img = Image.open(io.BytesIO(img_data))
                                        img_ext = f".{img.format.lower()}" if img.format else ".png"
                                    except:
                                        img_ext = ".png"
                                else:
                                    img_ext = ".png"
                            
                            # Save image
                            img_url = self.image_handler.save_image(
                                img_data, file_id, image_counter, img_ext
                            )
                            
                            # Add image to markdown
                            markdown_parts.append(f'\n<img src="{img_url}" alt="Image {image_counter}" />\n\n')
                        except Exception as e:
                            logger.warning(f"Failed to extract image {img_file} from DOCX: {e}")
                            continue
            except Exception as e:
                logger.warning(f"Failed to extract images from DOCX: {e}")
            
            content = "\n\n".join(markdown_parts)
            
            # Build structure
            structure = StructureBuilder.build_docx_structure(
                total_sections=len([p for p in markdown_parts if p.strip()])
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
        except Exception as e:
            logger.error(f"Failed to load DOCX file: {str(e)}", exc_info=True)
            raise LoaderError(f"Failed to load DOCX file: {str(e)}") from e
    
    def supports(self, doc_type: DocumentType) -> bool:
        """Check if supports DOCX."""
        return doc_type == DocumentType.DOCX
