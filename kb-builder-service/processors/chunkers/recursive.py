"""Recursive text chunker."""
from typing import List
import hashlib
from .base import BaseChunker
from models.document import Document
from models.chunk import Chunk


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
        
        # Handle empty or very short documents
        if not text or len(text.strip()) == 0:
            return []
        
        chunks = []
        current_pos = 0
        chunk_index = 0
        
        # Calculate max iterations more safely
        # Ensure we can make progress: at least move by (chunk_size - overlap) each iteration
        min_progress = max(1, self.chunk_size - self.chunk_overlap)
        max_iterations = (len(text) // min_progress) + 100  # Safety buffer
        iteration = 0
        last_pos = -1  # Track last position to detect stuck loops
        
        while current_pos < len(text) and iteration < max_iterations:
            iteration += 1
            
            # Safety check: if we haven't moved, force progress
            if current_pos == last_pos:
                # Force move forward by at least 1 character
                current_pos += 1
                if current_pos >= len(text):
                    break
            
            last_pos = current_pos
            
            # Skip whitespace at start
            while current_pos < len(text) and text[current_pos].isspace():
                current_pos += 1
            
            if current_pos >= len(text):
                break
            
            # Find best split point
            end_pos = min(current_pos + self.chunk_size, len(text))
            chunk_text = text[current_pos:end_pos]
            
            # Try to split at separator (only if not at end of text)
            if end_pos < len(text):
                best_sep_pos = -1
                for sep in self.separators:
                    if not sep:  # Skip empty separator
                        continue
                    last_sep_pos = chunk_text.rfind(sep)
                    # Only use separator if it's not too early (at least 50% through chunk)
                    if last_sep_pos >= self.chunk_size * 0.5:
                        best_sep_pos = max(best_sep_pos, last_sep_pos)
                
                if best_sep_pos > 0:
                    # Find which separator was used
                    for sep in self.separators:
                        if not sep:
                            continue
                        if chunk_text.rfind(sep) == best_sep_pos:
                            chunk_text = chunk_text[:best_sep_pos + len(sep)]
                            end_pos = current_pos + len(chunk_text)
                            break
            
            # Ensure we make progress - end_pos must be > current_pos
            if end_pos <= current_pos:
                end_pos = min(current_pos + 1, len(text))
                chunk_text = text[current_pos:end_pos]
            
            # Strip and check if chunk has content
            chunk_text_stripped = chunk_text.strip()
            if not chunk_text_stripped:
                # Empty chunk, skip it and move forward
                current_pos = end_pos
                continue
            
            # Create chunk
            chunk_id = self._generate_chunk_id(document.source, chunk_index)
            # Get file_path from metadata if available
            file_path = document.metadata.get("file_path") if document.metadata else None
            chunk = Chunk(
                text=chunk_text_stripped,
                chunk_id=chunk_id,
                document_id=document.source,  # Original filename
                chunk_index=chunk_index,
                file_path=file_path,  # Actual file path
                metadata={
                    **document.metadata,
                    "chunk_size": len(chunk_text_stripped),
                    "start_pos": current_pos,
                    "end_pos": end_pos
                }
            )
            chunks.append(chunk)
            
            # Move position with overlap, ensure we always make progress
            # Calculate next position: move back by overlap, but ensure we advance
            overlap_amount = min(self.chunk_overlap, len(chunk_text_stripped))
            next_pos = end_pos - overlap_amount
            
            # Ensure we always move forward
            if next_pos <= current_pos:
                # If overlap would cause us to go backwards or stay same, 
                # move forward by at least half the chunk size
                next_pos = current_pos + max(1, self.chunk_size // 2)
            
            # Ensure we don't exceed text length
            if next_pos >= len(text):
                break
            
            current_pos = next_pos
            chunk_index += 1
        
        # Only raise error if we didn't finish processing the document
        # If current_pos >= len(text), we successfully processed everything
        if iteration >= max_iterations and current_pos < len(text):
            raise RuntimeError(
                f"Chunking exceeded maximum iterations ({max_iterations}). "
                f"Possible infinite loop. Text length: {len(text)}, "
                f"Current position: {current_pos}, Chunks created: {len(chunks)}"
            )
        
        # If we have remaining text that wasn't processed, create a final chunk
        if current_pos < len(text):
            remaining_text = text[current_pos:].strip()
            if remaining_text:
                chunk_id = self._generate_chunk_id(document.source, chunk_index)
                # Get file_path from metadata if available
                file_path = document.metadata.get("file_path") if document.metadata else None
                chunk = Chunk(
                    text=remaining_text,
                    chunk_id=chunk_id,
                    document_id=document.source,  # Original filename
                    chunk_index=chunk_index,
                    file_path=file_path,  # Actual file path
                    metadata={
                        **document.metadata,
                        "chunk_size": len(remaining_text),
                        "start_pos": current_pos,
                        "end_pos": len(text)
                    }
                )
                chunks.append(chunk)
        
        return chunks
    
    def _generate_chunk_id(self, document_id: str, chunk_index: int) -> str:
        """Generate unique chunk ID."""
        content = f"{document_id}_{chunk_index}"
        return hashlib.md5(content.encode()).hexdigest()

