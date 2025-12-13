"""PDF chunker - extends MarkdownChunker."""
from typing import List
from models.document import Document
from models.chunk import Chunk
from .markdown_chunker import MarkdownChunker
from utils.logger import get_logger

logger = get_logger(__name__)


class PDFChunker(MarkdownChunker):
    """
    PDF-specific chunker.
    
    Note: In unified Markdown architecture, PDF content is already converted to Markdown.
    This class extends MarkdownChunker and uses MarkdownLocation directly.
    """
    
    def chunk(self, document: Document) -> List[Chunk]:
        """
        Split PDF document into chunks.
        
        Since PDF content is already Markdown, we can use the parent's chunk method directly.
        """
        # Use parent's chunk method (already creates MarkdownLocation)
        chunks = super().chunk(document)
        
        logger.info(f"Created {len(chunks)} chunks from PDF (using MarkdownChunker)")
        return chunks
