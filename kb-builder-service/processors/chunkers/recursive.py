"""Recursive text chunker."""
from typing import List, Tuple
import hashlib
import re
from .base import BaseChunker
from models.document import Document
from models.chunk import Chunk


class RecursiveChunker(BaseChunker):
    """Recursive chunker with overlap."""
    
    def __init__(
        self,
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
        separators: List[str] = None,
        min_chunk_size: int = 100  # Minimum chunk size to avoid creating chunks that are too short
    ):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        # Improved separator priority: semantic boundaries first
        self.separators = separators or ["\n\n\n", "\n\n", ". ", "。", "！", "？", " ", ""]
        self.min_chunk_size = min_chunk_size
        # HTML tag regex for identifying and protecting HTML tags
        self.html_tag_pattern = re.compile(r'<[^>]+>')
        # Special marker patterns (for protecting structured markers)
        self.special_markers = re.compile(r'<(page|paragraph|heading|table|code_block)[^>]*>', re.IGNORECASE)
    
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
            
            # Find best split point with HTML tag protection
            end_pos = min(current_pos + self.chunk_size, len(text))
            chunk_text = text[current_pos:end_pos]
            
            # Try to split at separator (only if not at end of text)
            if end_pos < len(text):
                # First, check if we're in the middle of an HTML tag or special marker
                end_pos = self._find_safe_split_point(text, current_pos, end_pos)
                chunk_text = text[current_pos:end_pos]
                
                # Try to find separator at safe position
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
                            # Re-check safety after separator split
                            end_pos = self._find_safe_split_point(text, current_pos, end_pos)
                            chunk_text = text[current_pos:end_pos]
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
            
            # Check minimum chunk size (unless it's the last chunk)
            if len(chunk_text_stripped) < self.min_chunk_size and end_pos < len(text):
                # Try to extend chunk to meet minimum size
                extended_end = min(current_pos + self.chunk_size * 1.5, len(text))
                extended_text = text[current_pos:extended_end]
                # Find next safe split point in extended text
                safe_extended_end = self._find_safe_split_point(text, current_pos, extended_end)
                extended_chunk = text[current_pos:safe_extended_end].strip()
                
                # Only use extended chunk if it's reasonable size
                if len(extended_chunk) >= self.min_chunk_size and len(extended_chunk) <= self.chunk_size * 1.5:
                    chunk_text = text[current_pos:safe_extended_end]
                    chunk_text_stripped = extended_chunk
                    end_pos = safe_extended_end
                # Otherwise, keep original chunk (will be merged later if needed)
            
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
            
            # Smart overlap: try to overlap at semantic boundary (sentence/paragraph end)
            if next_pos > current_pos:
                # Look for semantic boundary in overlap region
                overlap_text = text[next_pos:end_pos]
                for sep in ["\n\n", ". ", "。", "！", "？"]:
                    sep_pos = overlap_text.find(sep)
                    if sep_pos >= 0:
                        next_pos = next_pos + sep_pos + len(sep)
                        break
            
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
    
    def _find_safe_split_point(self, text: str, start: int, proposed_end: int) -> int:
        """Find a safe split point that doesn't break HTML tags or special markers."""
        end_pos = proposed_end
        
        # Check if we're in the middle of an HTML tag
        # Look backwards from proposed_end to find unclosed tag
        check_start = max(start, proposed_end - 200)  # Check last 200 chars
        check_text = text[check_start:proposed_end]
        
        # Find last '<' that might be an unclosed tag
        last_open_tag = check_text.rfind('<')
        if last_open_tag >= 0:
            # Check if this tag is closed
            tag_end = check_text.find('>', last_open_tag)
            if tag_end == -1:
                # Unclosed tag, find the closing '>'
                remaining = text[proposed_end:]
                closing_tag = remaining.find('>')
                if closing_tag != -1 and closing_tag < 100:  # Within reasonable distance
                    end_pos = proposed_end + closing_tag + 1
        
        # Check if we're in the middle of a special marker (page, paragraph, etc.)
        check_text_full = text[start:proposed_end]
        # Find last special marker start
        for match in self.special_markers.finditer(check_text_full):
            marker_start = match.start()
            marker_text = match.group(0)
            # Check if marker is closed
            if '</' not in check_text_full[marker_start:]:
                # Find closing tag
                marker_name = match.group(1)
                closing_pattern = f'</{marker_name}>'
                remaining = text[proposed_end:]
                closing_pos = remaining.find(closing_pattern)
                if closing_pos != -1 and closing_pos < 500:  # Within reasonable distance
                    end_pos = proposed_end + closing_pos + len(closing_pattern)
        
        # Check for unclosed HTML tags (img, br, etc. are self-closing, but others need closing)
        # Look for common tags that need closing
        unclosed_tags = ['<img', '<a ', '<table', '<div', '<span', '<p ', '<h1', '<h2', '<h3']
        for tag in unclosed_tags:
            tag_pos = check_text_full.rfind(tag)
            if tag_pos >= 0:
                # Check if it's a self-closing tag or has closing
                tag_snippet = check_text_full[tag_pos:min(tag_pos + 100, len(check_text_full))]
                if '/>' not in tag_snippet and f'</{tag[1:].split()[0]}>' not in check_text_full[tag_pos:]:
                    # Might be unclosed, but img and br are self-closing, so only worry about others
                    if tag not in ['<img']:
                        # Try to find closing tag
                        tag_name = tag[1:].split()[0] if ' ' in tag[1:] else tag[1:]
                        closing_tag = f'</{tag_name}>'
                        remaining = text[proposed_end:]
                        closing_pos = remaining.find(closing_tag)
                        if closing_pos != -1 and closing_pos < 500:
                            end_pos = proposed_end + closing_pos + len(closing_tag)
        
        return end_pos
    
    def _generate_chunk_id(self, document_id: str, chunk_index: int) -> str:
        """Generate unique chunk ID."""
        content = f"{document_id}_{chunk_index}"
        return hashlib.md5(content.encode()).hexdigest()

