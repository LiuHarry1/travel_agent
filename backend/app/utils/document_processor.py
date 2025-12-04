"""Document processing utilities for chunking and splitting documents."""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import List, Optional

from app.logger import get_logger

logger = get_logger(__name__)


@dataclass
class DocumentChunk:
    """Represents a chunk of a document."""
    
    text: str
    chunk_index: int
    start_pos: int
    end_pos: int
    metadata: Optional[dict] = None
    
    def __post_init__(self):
        """Initialize default metadata if not provided."""
        if self.metadata is None:
            self.metadata = {}


class DocumentChunker:
    """Document chunker with intelligent splitting strategies."""
    
    def __init__(
        self,
        chunk_size: int = 500,
        chunk_overlap: int = 50,
        min_chunk_size: int = 100,
    ):
        """
        Initialize document chunker.
        
        Args:
            chunk_size: Maximum size of each chunk in characters
            chunk_overlap: Number of characters to overlap between chunks
            min_chunk_size: Minimum size of a chunk (chunks smaller than this will be merged)
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.min_chunk_size = min_chunk_size
    
    def chunk_markdown(self, content: str, file_name: Optional[str] = None) -> List[DocumentChunk]:
        """
        Chunk markdown content using hybrid strategy:
        - Priority: Split by paragraph/heading boundaries
        - Fallback: Split by character count if segment exceeds threshold
        
        Args:
            content: Markdown content to chunk
            file_name: Optional file name for metadata
            
        Returns:
            List of DocumentChunk objects
        """
        if not content or not content.strip():
            return []
        
        # First, split by headings and paragraphs (preserving structure)
        segments = self._split_by_structure(content)
        
        # Then process each segment with size-aware chunking
        chunks = []
        chunk_index = 0
        
        for segment in segments:
            if len(segment) <= self.chunk_size:
                # Segment fits in one chunk
                chunk = DocumentChunk(
                    text=segment,
                    chunk_index=chunk_index,
                    start_pos=content.find(segment),
                    end_pos=content.find(segment) + len(segment),
                    metadata={
                        "file_name": file_name,
                        "strategy": "structure_boundary",
                    },
                )
                chunks.append(chunk)
                chunk_index += 1
            else:
                # Segment is too large, split by character count with overlap
                sub_chunks = self._split_by_char_count(segment, chunk_index)
                chunks.extend(sub_chunks)
                chunk_index += len(sub_chunks)
        
        # Merge very small chunks with adjacent chunks
        chunks = self._merge_small_chunks(chunks, content)
        
        logger.info(f"Created {len(chunks)} chunks from document (chunk_size={self.chunk_size}, overlap={self.chunk_overlap})")
        return chunks
    
    def _split_by_structure(self, content: str) -> List[str]:
        """
        Split content by markdown structure (headings, paragraphs).
        
        Returns:
            List of text segments
        """
        segments = []
        
        # Pattern to match markdown headings (# ## ### etc.)
        heading_pattern = re.compile(r'^(#{1,6}\s+.+)$', re.MULTILINE)
        
        # Find all heading positions
        headings = []
        for match in heading_pattern.finditer(content):
            headings.append((match.start(), match.end(), match.group()))
        
        # Split by headings and paragraphs
        if not headings:
            # No headings, split by paragraphs (double newlines)
            segments = [s.strip() for s in re.split(r'\n\n+', content) if s.strip()]
        else:
            # Split by headings, preserving heading with following content
            last_pos = 0
            for i, (start, end, heading_text) in enumerate(headings):
                # Get content before this heading
                if start > last_pos:
                    prev_content = content[last_pos:start].strip()
                    if prev_content:
                        segments.append(prev_content)
                
                # Get content after this heading (until next heading or end)
                next_start = headings[i + 1][0] if i + 1 < len(headings) else len(content)
                heading_content = content[start:next_start].strip()
                if heading_content:
                    segments.append(heading_content)
                
                last_pos = next_start
            
            # Add remaining content after last heading
            if last_pos < len(content):
                remaining = content[last_pos:].strip()
                if remaining:
                    segments.append(remaining)
        
        # Further split very long segments by paragraphs
        final_segments = []
        for segment in segments:
            if len(segment) <= self.chunk_size * 2:
                # Segment is not too long, keep as is
                final_segments.append(segment)
            else:
                # Split by paragraphs
                paragraphs = [p.strip() for p in re.split(r'\n\n+', segment) if p.strip()]
                final_segments.extend(paragraphs)
        
        return [s for s in final_segments if s.strip()]
    
    def _split_by_char_count(self, text: str, start_index: int) -> List[DocumentChunk]:
        """
        Split text by character count with overlap.
        
        Args:
            text: Text to split
            start_index: Starting chunk index
            
        Returns:
            List of DocumentChunk objects
        """
        chunks = []
        start = 0
        chunk_idx = start_index
        
        while start < len(text):
            end = start + self.chunk_size
            
            # If not at the end, try to break at a sentence or word boundary
            if end < len(text):
                # Try to break at sentence boundary (., !, ?)
                sentence_end = max(
                    text.rfind('.', start, end),
                    text.rfind('!', start, end),
                    text.rfind('?', start, end),
                    text.rfind('\n', start, end),
                )
                
                if sentence_end > start + self.min_chunk_size:
                    end = sentence_end + 1
                else:
                    # Try to break at word boundary
                    word_end = text.rfind(' ', start, end)
                    if word_end > start + self.min_chunk_size:
                        end = word_end + 1
            
            chunk_text = text[start:end].strip()
            if chunk_text:
                chunk = DocumentChunk(
                    text=chunk_text,
                    chunk_index=chunk_idx,
                    start_pos=start,
                    end_pos=end,
                    metadata={
                        "strategy": "char_count",
                    },
                )
                chunks.append(chunk)
                chunk_idx += 1
            
            # Move start position with overlap
            start = end - self.chunk_overlap
            if start >= len(text):
                break
        
        return chunks
    
    def _merge_small_chunks(self, chunks: List[DocumentChunk], original_content: str) -> List[DocumentChunk]:
        """
        Merge chunks that are too small with adjacent chunks.
        
        Args:
            chunks: List of chunks to process
            original_content: Original document content for position recalculation
            
        Returns:
            List of merged chunks
        """
        if not chunks:
            return chunks
        
        merged = []
        i = 0
        
        while i < len(chunks):
            current = chunks[i]
            
            # If chunk is too small, try to merge with next
            if len(current.text) < self.min_chunk_size and i + 1 < len(chunks):
                next_chunk = chunks[i + 1]
                
                # Check if merging would exceed chunk_size
                merged_text = current.text + "\n\n" + next_chunk.text
                if len(merged_text) <= self.chunk_size * 1.5:  # Allow some flexibility
                    # Merge chunks
                    merged_chunk = DocumentChunk(
                        text=merged_text,
                        chunk_index=current.chunk_index,
                        start_pos=current.start_pos,
                        end_pos=next_chunk.end_pos,
                        metadata={
                            **current.metadata,
                            "merged": True,
                            "original_chunks": 2,
                        },
                    )
                    merged.append(merged_chunk)
                    i += 2  # Skip next chunk as it's merged
                    continue
            
            merged.append(current)
            i += 1
        
        # Recalculate positions based on original content
        for chunk in merged:
            chunk.start_pos = original_content.find(chunk.text[:50])  # Approximate
            chunk.end_pos = chunk.start_pos + len(chunk.text)
        
        return merged
    
    def chunk_text(self, content: str, file_name: Optional[str] = None) -> List[DocumentChunk]:
        """
        Chunk plain text content (fallback method).
        
        Args:
            content: Text content to chunk
            file_name: Optional file name for metadata
            
        Returns:
            List of DocumentChunk objects
        """
        return self._split_by_char_count(content, 0)



