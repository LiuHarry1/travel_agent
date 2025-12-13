"""Markdown-specific chunker using two-stage splitting: headers then characters."""
from typing import List
import hashlib
from .base import BaseChunker
from .langchain_utils import create_tiktoken_splitter, create_markdown_header_splitter
from models.document import Document
from models.chunk import Chunk
from models.location.markdown_location import MarkdownLocation
from utils.logger import get_logger

logger = get_logger(__name__)


class MarkdownChunker(BaseChunker):
    """Markdown-specific chunker using two-stage splitting: headers then characters."""
    
    def __init__(
        self,
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
        min_chunk_size: int = 100,
        encoding_name: str = "cl100k_base"
    ):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.min_chunk_size = min_chunk_size
        self.encoding_name = encoding_name
        
        # Stage 1: Markdown header splitter
        self.header_splitter = create_markdown_header_splitter()
        
        # Stage 2: Character-level splitter with tiktoken
        self.char_splitter = create_tiktoken_splitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            encoding_name=encoding_name
        )
    
    def chunk(self, document: Document) -> List[Chunk]:
        """Split Markdown document into chunks using two-stage splitting."""
        text = document.content
        
        if not text or len(text.strip()) == 0:
            return []
        
        # Stage 1: Split by headers
        # MarkdownHeaderTextSplitter.split_text returns a list of Document objects
        header_splits = self.header_splitter.split_text(text)
        
        # Stage 2: Split each header section by characters
        all_chunks = []
        chunk_index = 0
        text_offset = 0  # Track position in original text
        
        for header_doc in header_splits:
            # Get header metadata and content
            # header_doc is a Document object with page_content and metadata
            header_metadata = getattr(header_doc, 'metadata', {})
            header_content = getattr(header_doc, 'page_content', str(header_doc))
            
            # Find the header section's position in original text
            header_start_pos = text.find(header_content, text_offset)
            if header_start_pos == -1:
                # If not found, try from beginning
                header_start_pos = text.find(header_content)
            if header_start_pos == -1:
                # Fallback: use current offset
                header_start_pos = text_offset
            
            # Split header section by characters
            char_splits = self.char_splitter.split_text(header_content)
            header_content_offset = 0  # Track position within header section
            
            for char_chunk_text in char_splits:
                char_chunk_text = char_chunk_text.strip()
                if not char_chunk_text:
                    continue
                
                # Find position within header section
                chunk_in_header_pos = header_content.find(char_chunk_text, header_content_offset)
                if chunk_in_header_pos == -1:
                    # Fallback: use header_content_offset
                    chunk_in_header_pos = header_content_offset
                
                # Calculate absolute position in original text
                start_pos = header_start_pos + chunk_in_header_pos
                end_pos = start_pos + len(char_chunk_text)
                
                # Update offsets
                header_content_offset = chunk_in_header_pos + len(char_chunk_text)
                text_offset = max(text_offset, end_pos)
                
                # Generate chunk ID
                chunk_id = self._generate_chunk_id(document.source, chunk_index)
                
                # Get file_path from metadata if available
                file_path = document.metadata.get("file_path") if document.metadata else None
                
                # Create location using MarkdownLocation
                location = MarkdownLocation(
                    start_char=start_pos,
                    end_char=end_pos,
                    metadata={
                        "source": document.metadata.get("file_name", document.source),
                    }
                )
                
                # Create chunk with header metadata
                chunk = Chunk(
                    text=char_chunk_text,
                    chunk_id=chunk_id,
                    document_id=document.source,
                    chunk_index=chunk_index,
                    file_path=file_path,
                    location=location,
                    metadata={
                        **document.metadata,
                        **header_metadata,  # Include header metadata
                        "chunk_size": len(char_chunk_text),
                        "start_pos": start_pos,
                        "end_pos": end_pos
                    }
                )
                all_chunks.append(chunk)
                chunk_index += 1
        
        logger.info(f"Created {len(all_chunks)} chunks from Markdown document")
        return all_chunks
    
    def _generate_chunk_id(self, document_id: str, chunk_index: int) -> str:
        """Generate unique chunk ID."""
        content = f"{document_id}_{chunk_index}"
        return hashlib.md5(content.encode()).hexdigest()
