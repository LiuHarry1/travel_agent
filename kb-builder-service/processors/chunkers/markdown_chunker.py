"""Markdown-specific chunker using RecursiveCharacterTextSplitter with code block protection."""
from typing import List, Optional, Tuple, Dict
import re
import hashlib
import tiktoken
from .base import BaseChunker
from .langchain_utils import create_tiktoken_splitter
from models.document import Document
from models.chunk import Chunk, ChunkLocation
from utils.logger import get_logger

logger = get_logger(__name__)


class MarkdownChunker(BaseChunker):
    """Markdown-specific chunker using RecursiveCharacterTextSplitter with code block protection."""
    
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
        
        # Create LangChain splitter with tiktoken
        self.splitter = create_tiktoken_splitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            encoding_name=encoding_name
        )
        
        # Create tiktoken encoder for token counting
        self.enc = tiktoken.get_encoding(encoding_name)
        
        # Code block pattern: matches ```language\n...\n```
        self.code_block_pattern = re.compile(
            r'```(\w+)?\n(.*?)```',
            re.DOTALL
        )
    
    def chunk(self, document: Document) -> List[Chunk]:
        """Split Markdown document into chunks, protecting code blocks."""
        text = document.content
        
        if not text or len(text.strip()) == 0:
            return []
        
        # Step 1: Extract code blocks and replace with placeholders
        text_with_placeholders, code_blocks = self._extract_code_blocks(text)
        
        # Step 2: Use RecursiveCharacterTextSplitter for non-code-block text
        text_chunks = self.splitter.split_text(text_with_placeholders)
        
        # Step 3: Convert to Chunk objects and restore code blocks
        chunks = []
        current_pos = 0
        
        for chunk_index, chunk_text in enumerate(text_chunks):
            chunk_text = chunk_text.strip()
            if not chunk_text:
                continue
            
            # Check minimum chunk size (unless it's the last chunk)
            if chunk_index < len(text_chunks) - 1:
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
            
            # Restore code blocks in chunk
            chunk_text = self._restore_code_blocks(chunk_text, code_blocks)
            
            # Calculate position in original text
            start_pos = text.find(chunk_text, current_pos)
            if start_pos == -1:
                # Fallback: use current_pos
                start_pos = current_pos
            end_pos = start_pos + len(chunk_text)
            current_pos = end_pos
            
            # Find code block indices in this chunk
            code_block_index = self._find_code_block_index(chunk_text, text, start_pos, code_blocks)
            
            # Generate chunk ID
            chunk_id = self._generate_chunk_id(document.source, chunk_index)
            
            # Get file_path from metadata if available
            file_path = document.metadata.get("file_path") if document.metadata else None
            
            # Create location
            location = ChunkLocation(
                start_char=start_pos,
                end_char=end_pos,
                code_block_index=code_block_index
            )
            
            # Create chunk
            chunk = Chunk(
                text=chunk_text,
                chunk_id=chunk_id,
                document_id=document.source,
                chunk_index=chunk_index,
                file_path=file_path,
                location=location,
                metadata={
                    **document.metadata,
                    "chunk_size": len(chunk_text),
                    "start_pos": start_pos,
                    "end_pos": end_pos,
                    "content_type": "text"
                }
            )
            chunks.append(chunk)
        
        logger.info(f"Created {len(chunks)} chunks from Markdown document")
        return chunks
    
    def _extract_code_blocks(self, text: str) -> Tuple[str, Dict[int, Dict]]:
        """
        Extract code blocks from text and replace with placeholders.
        
        Returns:
            (text_with_placeholders, code_blocks_dict)
        """
        code_blocks = {}
        text_with_placeholders = text
        code_block_id = 0
        
        for match in self.code_block_pattern.finditer(text):
            language = match.group(1) or ""
            code_content = match.group(2)
            
            # Store code block
            code_blocks[code_block_id] = {
                'language': language,
                'content': code_content,
                'full_match': match.group(0),
                'start_pos': match.start(),
                'end_pos': match.end()
            }
            
            # Replace with placeholder
            placeholder = f'<CODE_BLOCK_PLACEHOLDER_{code_block_id}>'
            text_with_placeholders = text_with_placeholders.replace(
                match.group(0),
                placeholder,
                1
            )
            
            code_block_id += 1
        
        return text_with_placeholders, code_blocks
    
    def _restore_code_blocks(self, chunk_text: str, code_blocks: Dict[int, Dict]) -> str:
        """Restore code blocks from placeholders in chunk text."""
        restored_text = chunk_text
        
        # Find all placeholders in chunk
        placeholder_pattern = re.compile(r'<CODE_BLOCK_PLACEHOLDER_(\d+)>')
        for match in placeholder_pattern.finditer(chunk_text):
            code_block_id = int(match.group(1))
            code_block = code_blocks.get(code_block_id)
            
            if code_block:
                # Restore the full code block
                restored_text = restored_text.replace(
                    match.group(0),
                    code_block['full_match'],
                    1
                )
        
        return restored_text
    
    def _find_code_block_index(
        self,
        chunk_text: str,
        full_text: str,
        chunk_start_pos: int,
        code_blocks: Dict[int, Dict]
    ) -> Optional[int]:
        """Find the code block index if this chunk contains a code block."""
        # Check if chunk contains any code block placeholders
        placeholder_pattern = re.compile(r'<CODE_BLOCK_PLACEHOLDER_(\d+)>')
        match = placeholder_pattern.search(chunk_text)
        
        if match:
            code_block_id = int(match.group(1))
            code_block = code_blocks.get(code_block_id)
            
            if code_block:
                # Find the index of this code block in the original document
                # by checking which code block's position overlaps with chunk
                for idx, (cb_id, cb_data) in enumerate(code_blocks.items()):
                    if cb_id == code_block_id:
                        return idx
                
                # If not found by ID, find by position
                chunk_end_pos = chunk_start_pos + len(chunk_text)
                for idx, (cb_id, cb_data) in enumerate(code_blocks.items()):
                    cb_start = cb_data['start_pos']
                    cb_end = cb_data['end_pos']
                    if cb_start >= chunk_start_pos and cb_end <= chunk_end_pos:
                        return idx
        
        return None
    
    def _generate_chunk_id(self, document_id: str, chunk_index: int) -> str:
        """Generate unique chunk ID."""
        content = f"{document_id}_{chunk_index}"
        return hashlib.md5(content.encode()).hexdigest()
