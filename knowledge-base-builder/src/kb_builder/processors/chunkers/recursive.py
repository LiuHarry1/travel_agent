"""Recursive text chunker."""
from typing import List
import hashlib
from .base import BaseChunker
from ...models.document import Document
from ...models.chunk import Chunk


class RecursiveChunker(BaseChunker):
    """Recursive chunker with overlap."""
    
    def __init__(
        self,
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
        separators: List[str] = None
    ):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.separators = separators or ["\n\n", "\n", " ", ""]
    
    def chunk(self, document: Document) -> List[Chunk]:
        """Split document into chunks."""
        text = document.content
        chunks = []
        
        current_pos = 0
        chunk_index = 0
        
        while current_pos < len(text):
            # Find best split point
            end_pos = min(current_pos + self.chunk_size, len(text))
            chunk_text = text[current_pos:end_pos]
            
            # Try to split at separator
            if end_pos < len(text):
                for sep in self.separators:
                    last_sep_pos = chunk_text.rfind(sep)
                    if last_sep_pos > self.chunk_size * 0.5:  # Don't split too early
                        chunk_text = chunk_text[:last_sep_pos + len(sep)]
                        end_pos = current_pos + len(chunk_text)
                        break
            
            # Create chunk
            chunk_id = self._generate_chunk_id(document.source, chunk_index)
            chunk = Chunk(
                text=chunk_text.strip(),
                chunk_id=chunk_id,
                document_id=document.source,
                chunk_index=chunk_index,
                metadata={
                    **document.metadata,
                    "chunk_size": len(chunk_text),
                    "start_pos": current_pos,
                    "end_pos": end_pos
                }
            )
            chunks.append(chunk)
            
            # Move position with overlap
            current_pos = end_pos - self.chunk_overlap
            chunk_index += 1
        
        return chunks
    
    def _generate_chunk_id(self, document_id: str, chunk_index: int) -> str:
        """Generate unique chunk ID."""
        content = f"{document_id}_{chunk_index}"
        return hashlib.md5(content.encode()).hexdigest()

