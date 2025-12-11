"""Recursive text chunker using LangChain with tiktoken."""
from typing import List
import hashlib
import tiktoken
from .base import BaseChunker
from .langchain_utils import create_tiktoken_splitter
from models.document import Document
from models.chunk import Chunk


class RecursiveChunker(BaseChunker):
    """Recursive chunker using LangChain RecursiveCharacterTextSplitter with tiktoken."""
    
    def __init__(
        self,
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
        encoding_name: str = "cl100k_base",
        separators: List[str] = None,
        min_chunk_size: int = 100
    ):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.encoding_name = encoding_name
        self.min_chunk_size = min_chunk_size
        
        # Create tiktoken encoder for token counting
        self.enc = tiktoken.get_encoding(encoding_name)
        
        # Create LangChain splitter with tiktoken
        self.splitter = create_tiktoken_splitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            encoding_name=encoding_name,
            separators=separators
        )
    
    def chunk(self, document: Document) -> List[Chunk]:
        """Split document into chunks using LangChain splitter."""
        text = document.content
        
        # Handle empty or very short documents
        if not text or len(text.strip()) == 0:
            return []
        
        # Use LangChain splitter to split text
        text_chunks = self.splitter.split_text(text)
        
        # Convert to Chunk objects
        chunks = []
        current_pos = 0
        
        for chunk_index, chunk_text in enumerate(text_chunks):
            chunk_text = chunk_text.strip()
            
            # Skip empty chunks
            if not chunk_text:
                continue
            
            # Check minimum chunk size (unless it's the last chunk)
            if chunk_index < len(text_chunks) - 1:
                # Calculate token count for minimum size check
                token_count = len(self.enc.encode(chunk_text))
                if token_count < self.min_chunk_size:
                    # Try to merge with next chunk if available
                    if chunk_index + 1 < len(text_chunks):
                        next_chunk = text_chunks[chunk_index + 1].strip()
                        merged_text = chunk_text + "\n\n" + next_chunk
                        merged_token_count = len(self.enc.encode(merged_text))
                        # Only merge if merged chunk is reasonable size
                        if merged_token_count <= self.chunk_size * 1.5:
                            chunk_text = merged_text
                            # Skip next chunk since we merged it
                            text_chunks[chunk_index + 1] = ""
            
            # Calculate position in original text
            start_pos = text.find(chunk_text, current_pos)
            if start_pos == -1:
                # Fallback: use current_pos
                start_pos = current_pos
            end_pos = start_pos + len(chunk_text)
            current_pos = end_pos
            
            # Generate chunk ID
            chunk_id = self._generate_chunk_id(document.source, chunk_index)
            
            # Get file_path from metadata if available
            file_path = document.metadata.get("file_path") if document.metadata else None
            
            # Create chunk
            chunk = Chunk(
                text=chunk_text,
                chunk_id=chunk_id,
                document_id=document.source,
                chunk_index=chunk_index,
                file_path=file_path,
                metadata={
                    **document.metadata,
                    "chunk_size": len(chunk_text),
                    "start_pos": start_pos,
                    "end_pos": end_pos
                }
            )
            chunks.append(chunk)
        
        return chunks
    
    def _generate_chunk_id(self, document_id: str, chunk_index: int) -> str:
        """Generate unique chunk ID."""
        content = f"{document_id}_{chunk_index}"
        return hashlib.md5(content.encode()).hexdigest()
