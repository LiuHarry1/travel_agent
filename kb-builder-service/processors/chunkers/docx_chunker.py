"""DOCX-specific chunker."""
from typing import List
import re
from .base import BaseChunker
from models.document import Document
from models.chunk import Chunk, ChunkLocation


class DOCXChunker(BaseChunker):
    """DOCX-specific chunker that respects paragraph boundaries."""
    
    def __init__(
        self,
        chunk_size: int = 1200,
        chunk_overlap: int = 200,
        min_chunk_size: int = 150
    ):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.min_chunk_size = min_chunk_size
        # Paragraph marker pattern
        self.paragraph_pattern = re.compile(r'<paragraph\s+index="(\d+)"[^>]*>', re.IGNORECASE)
        # Image tag pattern
        self.img_pattern = re.compile(r'<img[^>]+>', re.IGNORECASE)
    
    def chunk(self, document: Document) -> List[Chunk]:
        """Split DOCX document into chunks, respecting paragraph boundaries."""
        text = document.content
        
        if not text or len(text.strip()) == 0:
            return []
        
        chunks = []
        chunk_index = 0
        current_pos = 0
        
        # Chunk by paragraphs
        paragraphs = text.split('\n\n')
        
        current_chunk_parts = []
        current_chunk_size = 0
        current_paragraph_index = 0
        
        for para_idx, para in enumerate(paragraphs):
            para = para.strip()
            if not para:
                continue
            
            para_size = len(para)
            
            # If current chunk plus this paragraph would exceed size, save current chunk first
            if current_chunk_size + para_size > self.chunk_size and current_chunk_parts:
                # Create chunk
                chunk_text = '\n\n'.join(current_chunk_parts)
                location = ChunkLocation(
                    start_char=current_pos,
                    end_char=current_pos + len(chunk_text),
                    paragraph_index=current_paragraph_index
                )
                
                chunk = Chunk(
                    text=chunk_text,
                    chunk_id=self._generate_chunk_id(document.source, chunk_index),
                    document_id=document.source,
                    chunk_index=chunk_index,
                    file_path=document.metadata.get("file_path") if document.metadata else None,
                    location=location,
                    metadata={
                        **document.metadata,
                        "chunk_size": len(chunk_text),
                        "start_pos": current_pos,
                        "end_pos": current_pos + len(chunk_text)
                    }
                )
                chunks.append(chunk)
                
                # Overlap: keep last part
                overlap_text = '\n\n'.join(current_chunk_parts[-1:])
                current_chunk_parts = [overlap_text] if len(overlap_text) <= self.chunk_overlap else []
                current_chunk_size = len(overlap_text)
                current_pos += len(chunk_text) - len(overlap_text)
                chunk_index += 1
                current_paragraph_index = para_idx
            
            # If single paragraph exceeds chunk_size, need to split paragraph
            if para_size > self.chunk_size:
                # Save current chunk first
                if current_chunk_parts:
                    chunk_text = '\n\n'.join(current_chunk_parts)
                    location = ChunkLocation(
                        start_char=current_pos,
                        end_char=current_pos + len(chunk_text),
                        paragraph_index=current_paragraph_index
                    )
                    chunk = Chunk(
                        text=chunk_text,
                        chunk_id=self._generate_chunk_id(document.source, chunk_index),
                        document_id=document.source,
                        chunk_index=chunk_index,
                        file_path=document.metadata.get("file_path") if document.metadata else None,
                        location=location,
                        metadata={
                            **document.metadata,
                            "chunk_size": len(chunk_text),
                            "start_pos": current_pos,
                            "end_pos": current_pos + len(chunk_text)
                        }
                    )
                    chunks.append(chunk)
                    current_pos += len(chunk_text)
                    chunk_index += 1
                    current_chunk_parts = []
                    current_chunk_size = 0
                
                # Split large paragraph
                para_chunks = self._split_large_paragraph(
                    para,
                    document,
                    current_pos,
                    para_idx,
                    chunk_index
                )
                chunks.extend(para_chunks)
                chunk_index += len(para_chunks)
                if para_chunks:
                    current_pos = para_chunks[-1].metadata["end_pos"]
                    current_chunk_parts = []
                    current_chunk_size = 0
            else:
                # Add to current chunk
                current_chunk_parts.append(para)
                current_chunk_size += para_size + 2  # +2 for \n\n
                current_paragraph_index = para_idx
        
        # Process remaining chunk
        if current_chunk_parts:
            chunk_text = '\n\n'.join(current_chunk_parts)
            location = ChunkLocation(
                start_char=current_pos,
                end_char=current_pos + len(chunk_text),
                paragraph_index=current_paragraph_index
            )
            chunk = Chunk(
                text=chunk_text,
                chunk_id=self._generate_chunk_id(document.source, chunk_index),
                document_id=document.source,
                chunk_index=chunk_index,
                file_path=document.metadata.get("file_path") if document.metadata else None,
                location=location,
                metadata={
                    **document.metadata,
                    "chunk_size": len(chunk_text),
                    "start_pos": current_pos,
                    "end_pos": current_pos + len(chunk_text)
                }
            )
            chunks.append(chunk)
        
        return chunks
    
    def _split_large_paragraph(
        self,
        para: str,
        document: Document,
        start_pos: int,
        para_idx: int,
        start_chunk_index: int
    ) -> List[Chunk]:
        """Split a large paragraph into smaller chunks."""
        chunks = []
        chunk_index = start_chunk_index
        current_pos = 0
        
        while current_pos < len(para):
            end_pos = min(current_pos + self.chunk_size, len(para))
            chunk_text = para[current_pos:end_pos]
            
            # Try to split at sentence boundaries
            if end_pos < len(para):
                for sep in ['. ', '。', '！', '？', '\n']:
                    sep_pos = chunk_text.rfind(sep)
                    if sep_pos >= self.chunk_size * 0.5:
                        chunk_text = chunk_text[:sep_pos + len(sep)]
                        end_pos = current_pos + len(chunk_text)
                        break
            
            chunk_text = chunk_text.strip()
            if not chunk_text:
                current_pos = end_pos
                continue
            
            location = ChunkLocation(
                start_char=start_pos + current_pos,
                end_char=start_pos + end_pos,
                paragraph_index=para_idx
            )
            
            chunk = Chunk(
                text=chunk_text,
                chunk_id=self._generate_chunk_id(document.source, chunk_index),
                document_id=document.source,
                chunk_index=chunk_index,
                file_path=document.metadata.get("file_path") if document.metadata else None,
                location=location,
                metadata={
                    **document.metadata,
                    "chunk_size": len(chunk_text),
                    "start_pos": start_pos + current_pos,
                    "end_pos": start_pos + end_pos
                }
            )
            chunks.append(chunk)
            
            # Overlap
            overlap_amount = min(self.chunk_overlap, len(chunk_text))
            current_pos = max(current_pos + 1, end_pos - overlap_amount)
            chunk_index += 1
        
        return chunks
    
    def _generate_chunk_id(self, document_id: str, chunk_index: int) -> str:
        """Generate unique chunk ID."""
        import hashlib
        content = f"{document_id}_{chunk_index}"
        return hashlib.md5(content.encode()).hexdigest()

