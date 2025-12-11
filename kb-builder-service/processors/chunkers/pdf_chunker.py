"""PDF-specific chunker."""
from typing import List, Optional
import re
from .base import BaseChunker
from models.document import Document
from models.chunk import Chunk, ChunkLocation
from utils.logger import get_logger

logger = get_logger(__name__)


class PDFChunker(BaseChunker):
    """PDF-specific chunker that respects page boundaries and protects images."""
    
    def __init__(
        self,
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
        min_chunk_size: int = 100
    ):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.min_chunk_size = min_chunk_size
        # Page marker patterns
        self.page_pattern = re.compile(r'<page\s+page="(\d+)"[^>]*>', re.IGNORECASE)
        self.page_close_pattern = re.compile(r'</page>', re.IGNORECASE)
        # Image tag pattern
        self.img_pattern = re.compile(r'<img[^>]+>', re.IGNORECASE)
        # Table marker pattern
        self.table_pattern = re.compile(r'<table[^>]*>.*?</table>', re.DOTALL | re.IGNORECASE)
    
    def chunk(self, document: Document) -> List[Chunk]:
        """Split PDF document into chunks, respecting heading hierarchy or page boundaries."""
        text = document.content
        
        if not text or len(text.strip()) == 0:
            return []
        
        chunks = []
        chunk_index = 0
        
        # Try to use heading information for chunking
        # Check if PDF heading information exists
        pdf_headings = None
        if document.structure and document.structure.pdf_headings:
            pdf_headings = document.structure.pdf_headings
        
        # Find Markdown format headings (inserted in _load_pdf)
        heading_pattern = re.compile(r'^(#{1,6})\s+(.+)$', re.MULTILINE)
        all_headings = list(heading_pattern.finditer(text))
        
        # Filter out "Page X" pseudo-headings
        headings = []
        page_heading_pattern = re.compile(r'^Page\s+\d+$', re.IGNORECASE)
        for heading_match in all_headings:
            heading_text = heading_match.group(2).strip()
            # Skip "Page X" format headings
            if not page_heading_pattern.match(heading_text):
                headings.append(heading_match)
        
        # If headings exist, prioritize heading-based chunking
        if headings:
            logger.info(f"Using heading-based chunking for PDF with {len(headings)} headings (filtered {len(all_headings) - len(headings)} page markers)")
            return self._chunk_by_headings(text, document, headings, chunk_index)
        
        # If no headings, fall back to page-based chunking
        logger.info("No headings detected, falling back to page-based chunking")
        return self._chunk_by_pages(text, document)
    
    def _chunk_by_pages(self, text: str, document: Document) -> List[Chunk]:
        """Chunk by pages (original logic)."""
        chunks = []
        chunk_index = 0
        
        # Find all page markers
        page_matches = list(self.page_pattern.finditer(text))
        
        if not page_matches:
            # If no page markers, use recursive chunking
            from .recursive import RecursiveChunker
            recursive_chunker = RecursiveChunker(
                chunk_size=self.chunk_size,
                chunk_overlap=self.chunk_overlap,
                min_chunk_size=self.min_chunk_size
            )
            return recursive_chunker.chunk(document)
        
        # Chunk by pages
        for i, page_match in enumerate(page_matches):
            page_num = int(page_match.group(1))
            page_start = page_match.start()
            
            # Find page end position
            if i + 1 < len(page_matches):
                page_end = page_matches[i + 1].start()
            else:
                # Last page, find </page> tag
                close_match = self.page_close_pattern.search(text, page_start)
                page_end = close_match.end() if close_match else len(text)
            
            page_text = text[page_start:page_end]
            
            # Further chunk within page if needed
            page_chunks = self._chunk_within_page(
                page_text,
                document,
                page_num,
                page_start,
                chunk_index
            )
            chunks.extend(page_chunks)
            chunk_index += len(page_chunks)
        
        return chunks
    
    def _chunk_by_headings(self, text: str, document: Document, headings: List[re.Match], start_chunk_index: int) -> List[Chunk]:
        """Chunk by heading hierarchy (referencing markdown_chunker implementation)."""
        chunks = []
        chunk_index = start_chunk_index
        
        logger.info(f"Starting heading-based chunking with {len(headings)} headings")
        
        # Chunk by heading hierarchy
        for i, heading_match in enumerate(headings):
            heading_level = len(heading_match.group(1))
            heading_text = heading_match.group(2).strip()
            heading_start = heading_match.start()
            
            # Find next same-level or higher-level heading position
            if i + 1 < len(headings):
                next_heading_start = headings[i + 1].start()
                # If next heading level is higher, continue including
                next_level = len(headings[i + 1].group(1))
                if next_level > heading_level:
                    # Find next same-level or higher-level heading
                    for j in range(i + 2, len(headings)):
                        j_level = len(headings[j].group(1))
                        if j_level <= heading_level:
                            next_heading_start = headings[j].start()
                            break
                section_end = next_heading_start
            else:
                section_end = len(text)
            
            section_text = text[heading_start:section_end].strip()
            
            # Build heading path
            heading_path = self._build_heading_path(headings, i)
            
            # Extract page information (from <page> tags in section_text, before cleaning)
            page_num = None
            page_match = self.page_pattern.search(section_text)
            if page_match:
                page_num = int(page_match.group(1))
            
            # Clean page markers
            clean_section_text = self._clean_page_markers(section_text)
            
            # Skip sections that are too small (less than min_chunk_size)
            if len(clean_section_text.strip()) < self.min_chunk_size:
                # Try to merge with previous chunk if exists
                if chunks:
                    last_chunk = chunks[-1]
                    # Merge text
                    merged_text = last_chunk.text + "\n\n" + clean_section_text
                    if len(merged_text) <= self.chunk_size * 1.5:  # Allow moderate overflow
                        last_chunk.text = merged_text
                        last_chunk.location.end_char = section_end
                        last_chunk.metadata["chunk_size"] = len(merged_text)
                        last_chunk.metadata["end_pos"] = section_end
                        continue
                # If cannot merge, skip section that is too small
                continue
            
            # If section is too large, further chunk it
            if len(clean_section_text) > self.chunk_size:
                logger.debug(f"Section too large ({len(clean_section_text)} chars), splitting. heading_path: {heading_path}")
                section_chunks = self._chunk_within_section(
                    clean_section_text,  # Use cleaned text to avoid duplicate cleaning and position calculation errors
                    document,
                    heading_path,
                    heading_start,
                    chunk_index,
                    page_num
                )
                logger.debug(f"Section split into {len(section_chunks)} chunks")
                chunks.extend(section_chunks)
                chunk_index += len(section_chunks)
            else:
                # Entire section as one chunk
                location = ChunkLocation(
                    start_char=heading_start,
                    end_char=section_end,
                    heading_path=heading_path,
                    page_number=page_num
                )
                
                # Extract image information
                img_match = self.img_pattern.search(section_text)
                if img_match:
                    img_src_match = re.search(r'src="([^"]+)"', img_match.group(0))
                    if img_src_match:
                        location.image_url = img_src_match.group(1)
                    img_idx_match = re.search(r'image_index="(\d+)"', img_match.group(0))
                    if img_idx_match:
                        location.image_index = int(img_idx_match.group(1))
                
                chunk = Chunk(
                    text=clean_section_text,
                    chunk_id=self._generate_chunk_id(document.source, chunk_index),
                    document_id=document.source,
                    chunk_index=chunk_index,
                    file_path=document.metadata.get("file_path") if document.metadata else None,
                    location=location,
                    metadata={
                        **document.metadata,
                        "chunk_size": len(clean_section_text),
                        "start_pos": heading_start,
                        "end_pos": section_end,
                        "page_number": page_num
                    }
                )
                chunks.append(chunk)
                chunk_index += 1
        
        logger.info(f"Heading-based chunking completed: created {len(chunks)} chunks from {len(headings)} headings")
        return chunks
    
    def _chunk_within_page(
        self,
        page_text: str,
        document: Document,
        page_num: int,
        page_offset: int,
        start_chunk_index: int
    ) -> List[Chunk]:
        """Chunk within a single page, protecting images and tables."""
        chunks = []
        chunk_index = start_chunk_index
        current_pos = 0
        
        # Clean page markers
        clean_text = self._clean_page_markers(page_text)
        
        if not clean_text:
            return []
        
        # If page content is smaller than chunk_size, use as one chunk
        if len(clean_text) <= self.chunk_size:
            location = ChunkLocation(
                start_char=page_offset + current_pos,
                end_char=page_offset + len(page_text),
                page_number=page_num
            )
            # Extract image information
            img_match = self.img_pattern.search(clean_text)
            if img_match:
                img_src_match = re.search(r'src="([^"]+)"', img_match.group(0))
                if img_src_match:
                    location.image_url = img_src_match.group(1)
                img_idx_match = re.search(r'image_index="(\d+)"', img_match.group(0))
                if img_idx_match:
                    location.image_index = int(img_idx_match.group(1))
            
            # Debug: Log document metadata for first chunk
            if chunk_index == start_chunk_index:
                logger.info(f"Document metadata: {document.metadata}")
                logger.info(f"Document metadata keys: {list(document.metadata.keys()) if document.metadata else 'None'}")
            
            chunk = Chunk(
                text=clean_text,
                chunk_id=self._generate_chunk_id(document.source, chunk_index),
                document_id=document.source,
                chunk_index=chunk_index,
                file_path=document.metadata.get("file_path") if document.metadata else None,
                location=location,
                metadata={
                    **document.metadata,
                    "chunk_size": len(clean_text),
                    "start_pos": page_offset + current_pos,
                    "end_pos": page_offset + len(page_text),
                    "page_number": page_num
                }
            )
            
            # Debug: Log chunk metadata for first chunk
            if chunk_index == start_chunk_index:
                logger.info(f"Chunk metadata after creation: {chunk.metadata}")
                logger.info(f"Chunk metadata keys: {list(chunk.metadata.keys())}")
            chunks.append(chunk)
            return chunks
        
        # Page content is large, need further chunking
        # Use improved recursive chunking, but protect images and tables
        while current_pos < len(clean_text):
            end_pos = min(current_pos + self.chunk_size, len(clean_text))
            chunk_text = clean_text[current_pos:end_pos]
            
            # If not at text end, try to split at safe position
            if end_pos < len(clean_text):
                # Protect image tags
                chunk_text = self._protect_tags_in_chunk(chunk_text, clean_text, current_pos, end_pos)
                end_pos = current_pos + len(chunk_text)
            
            chunk_text = chunk_text.strip()
            if not chunk_text:
                current_pos = end_pos
                continue
            
            # 检查最小chunk大小
            if len(chunk_text) < self.min_chunk_size and end_pos < len(clean_text):
                # 尝试扩展
                extended_end = min(current_pos + self.chunk_size * 1.5, len(clean_text))
                extended_text = clean_text[current_pos:extended_end]
                extended_text = self._protect_tags_in_chunk(extended_text, clean_text, current_pos, extended_end)
                if len(extended_text.strip()) >= self.min_chunk_size:
                    chunk_text = extended_text.strip()
                    end_pos = current_pos + len(extended_text)
            
            location = ChunkLocation(
                start_char=page_offset + current_pos,
                end_char=page_offset + end_pos,
                page_number=page_num
            )
            
            # Extract image information
            img_match = self.img_pattern.search(chunk_text)
            if img_match:
                img_src_match = re.search(r'src="([^"]+)"', img_match.group(0))
                if img_src_match:
                    location.image_url = img_src_match.group(1)
                img_idx_match = re.search(r'image_index="(\d+)"', img_match.group(0))
                if img_idx_match:
                    location.image_index = int(img_idx_match.group(1))
            
            # Debug: Log document metadata for first chunk in page
            if chunk_index == start_chunk_index:
                logger.info(f"Document metadata (page chunk): {document.metadata}")
                logger.info(f"Document metadata keys (page chunk): {list(document.metadata.keys()) if document.metadata else 'None'}")
            
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
                    "start_pos": page_offset + current_pos,
                    "end_pos": page_offset + end_pos,
                    "page_number": page_num
                }
            )
            
            # Debug: Log chunk metadata for first chunk in page
            if chunk_index == start_chunk_index:
                logger.info(f"Chunk metadata after creation (page chunk): {chunk.metadata}")
                logger.info(f"Chunk metadata keys (page chunk): {list(chunk.metadata.keys())}")
            
            chunks.append(chunk)
            
            # Calculate next position (with overlap)
            overlap_amount = min(self.chunk_overlap, len(chunk_text))
            current_pos = max(current_pos + 1, end_pos - overlap_amount)
            chunk_index += 1
        
        return chunks
    
    def _build_heading_path(self, headings: List[re.Match], current_idx: int) -> List[str]:
        """Build heading path from root to current heading."""
        path = []
        current_level = len(headings[current_idx].group(1))
        current_text = headings[current_idx].group(2).strip()
        
        # Pattern to filter "Page X" pseudo-headings
        page_heading_pattern = re.compile(r'^Page\s+\d+$', re.IGNORECASE)
        
        # Search upward for parent headings
        for i in range(current_idx - 1, -1, -1):
            level = len(headings[i].group(1))
            heading_text = headings[i].group(2).strip()
            # Skip "Page X" format pseudo-headings
            if page_heading_pattern.match(heading_text):
                continue
            if level < current_level:
                path.insert(0, heading_text)
                current_level = level
                if level == 1:
                    break
        
        # Ensure current heading is not "Page X"
        if not page_heading_pattern.match(current_text):
            path.append(current_text)
        
        return path
    
    def _chunk_within_section(
        self,
        section_text: str,
        document: Document,
        heading_path: List[str],
        section_offset: int,
        start_chunk_index: int,
        page_num: Optional[int] = None
    ) -> List[Chunk]:
        """Chunk within a section, protecting images and tables."""
        chunks = []
        chunk_index = start_chunk_index
        current_pos = 0
        max_iterations = len(section_text) + 1000  # 防止无限循环
        iteration_count = 0
        
        # 清理页面标记
        clean_section_text = self._clean_page_markers(section_text)
        
        logger.debug(f"Chunking section of {len(clean_section_text)} chars, heading_path: {heading_path}, chunk_size={self.chunk_size}, min_chunk_size={self.min_chunk_size}")
        
        # 优化：如果section不太大（小于chunk_size * 1.5），直接作为一个chunk，避免过度分割
        if len(clean_section_text) <= int(self.chunk_size * 1.5):
            logger.debug(f"Section is small enough ({len(clean_section_text)} chars), creating single chunk")
            location = ChunkLocation(
                start_char=section_offset,
                end_char=section_offset + len(clean_section_text),
                heading_path=heading_path.copy(),
                page_number=page_num
            )
            
            # Extract image information
            img_match = self.img_pattern.search(clean_section_text)
            if img_match:
                img_src_match = re.search(r'src="([^"]+)"', img_match.group(0))
                if img_src_match:
                    location.image_url = img_src_match.group(1)
                img_idx_match = re.search(r'image_index="(\d+)"', img_match.group(0))
                if img_idx_match:
                    location.image_index = int(img_idx_match.group(1))
            
            chunk = Chunk(
                text=clean_section_text,
                chunk_id=self._generate_chunk_id(document.source, start_chunk_index),
                document_id=document.source,
                chunk_index=start_chunk_index,
                file_path=document.metadata.get("file_path") if document.metadata else None,
                location=location,
                metadata={
                    **document.metadata,
                    "chunk_size": len(clean_section_text),
                    "start_pos": section_offset,
                    "end_pos": section_offset + len(clean_section_text),
                    "page_number": page_num
                }
            )
            return [chunk]
        
        while current_pos < len(clean_section_text):
            iteration_count += 1
            if iteration_count > max_iterations:
                logger.error(f"Infinite loop detected in _chunk_within_section! current_pos={current_pos}, len={len(clean_section_text)}, chunks_created={len(chunks)}")
                break
            end_pos = min(current_pos + self.chunk_size, len(clean_section_text))
            
            # Prevent infinite loop: ensure end_pos is at least 1 greater than current_pos
            if end_pos <= current_pos:
                end_pos = min(current_pos + 1, len(clean_section_text))
            
            chunk_text = clean_section_text[current_pos:end_pos]
            
            # If not at text end, try to split at safe position
            if end_pos < len(clean_section_text):
                # Protect image and table tags
                protected_chunk = self._protect_tags_in_chunk(chunk_text, clean_section_text, current_pos, end_pos)
                # Only use it if protected_chunk is actually longer
                if len(protected_chunk) > len(chunk_text):
                    chunk_text = protected_chunk
                    end_pos = current_pos + len(chunk_text)
                # Ensure end_pos > current_pos again
                if end_pos <= current_pos:
                    end_pos = current_pos + 1
                    chunk_text = clean_section_text[current_pos:end_pos]
            
            # Record end_pos before strip for subsequent calculations
            original_end_pos = end_pos
            chunk_text = chunk_text.strip()
            
            # Note: strip only removes leading/trailing whitespace, should not change end_pos
            # The end_pos is based on original chunk_text, so it should remain unchanged
            
            if not chunk_text:
                # If empty after strip, this section is mostly whitespace, skip
                # Ensure at least advance 1 character to prevent infinite loop
                current_pos = max(current_pos + 1, end_pos)
                if current_pos >= len(clean_section_text):
                    break
                continue
            
            # Check minimum chunk size
            if len(chunk_text) < self.min_chunk_size:
                if end_pos < len(clean_section_text):
                    # Try to extend: extend to 1.5x chunk_size
                    extended_end = min(current_pos + int(self.chunk_size * 1.5), len(clean_section_text))
                    extended_text = clean_section_text[current_pos:extended_end]
                    extended_text = self._protect_tags_in_chunk(extended_text, clean_section_text, current_pos, extended_end)
                    extended_text_stripped = extended_text.strip()
                    if len(extended_text_stripped) >= self.min_chunk_size:
                        chunk_text = extended_text_stripped
                        end_pos = current_pos + len(extended_text)
                    else:
                        # Cannot extend to minimum size, try to merge with previous chunk
                        if chunks and chunk_index > start_chunk_index:
                            last_chunk = chunks[-1]
                            merged_text = last_chunk.text + "\n\n" + chunk_text
                            if len(merged_text) <= int(self.chunk_size * 1.5):
                                last_chunk.text = merged_text
                                last_chunk.location.end_char = section_offset + end_pos
                                last_chunk.metadata["chunk_size"] = len(merged_text)
                                last_chunk.metadata["end_pos"] = section_offset + end_pos
                                # Move to next position (considering overlap, but ensure at least 20% of chunk_size advance)
                                overlap_amount = min(self.chunk_overlap, len(merged_text))
                                min_advance = max(1, int(self.chunk_size * 0.2))
                                current_pos = max(current_pos + min_advance, end_pos - overlap_amount)
                                if current_pos >= len(clean_section_text):
                                    break
                                continue
                        # If cannot merge, skip chunk that is too small
                        # Jump directly to next reasonable split point (at least 50% of chunk_size advance)
                        # This avoids creating too many small chunks
                        skip_to = min(current_pos + max(self.chunk_size // 2, self.min_chunk_size * 2), len(clean_section_text))
                        current_pos = skip_to
                        if current_pos >= len(clean_section_text):
                            break
                        continue
                else:
                    # Reached text end, try to merge with previous chunk
                    if chunks and chunk_index > start_chunk_index:
                        last_chunk = chunks[-1]
                        merged_text = last_chunk.text + "\n\n" + chunk_text
                        last_chunk.text = merged_text
                        last_chunk.location.end_char = section_offset + end_pos
                        last_chunk.metadata["chunk_size"] = len(merged_text)
                        last_chunk.metadata["end_pos"] = section_offset + end_pos
                        # Ensure at least advance 1 character to prevent infinite loop
                        current_pos = max(current_pos + 1, end_pos)
                        continue
                    # If cannot merge and is last chunk, still add (to avoid losing content)
                    # But log warning
                    if len(chunk_text) < self.min_chunk_size:
                        logger.warning(f"Creating small chunk ({len(chunk_text)} chars) at end of section")
            
            location = ChunkLocation(
                start_char=section_offset + current_pos,
                end_char=section_offset + end_pos,
                heading_path=heading_path.copy(),
                page_number=page_num
            )
            
            # Extract image information
            img_match = self.img_pattern.search(chunk_text)
            if img_match:
                img_src_match = re.search(r'src="([^"]+)"', img_match.group(0))
                if img_src_match:
                    location.image_url = img_src_match.group(1)
                img_idx_match = re.search(r'image_index="(\d+)"', img_match.group(0))
                if img_idx_match:
                    location.image_index = int(img_idx_match.group(1))
            
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
                    "start_pos": section_offset + current_pos,
                    "end_pos": section_offset + end_pos,
                    "page_number": page_num
                }
            )
            chunks.append(chunk)
            
            # Overlap: calculate next chunk's starting position
            # Normally, next chunk should start from end_pos - overlap_amount
            overlap_amount = min(self.chunk_overlap, len(chunk_text))
            new_pos = end_pos - overlap_amount
            
            # Ensure position actually advances
            # If chunk is small (less than 30% of chunk_size), overlap may cause position to barely advance
            # Need to ensure at least 20% of chunk_size advance to avoid creating too many small chunks
            chunk_ratio = len(chunk_text) / self.chunk_size if self.chunk_size > 0 else 1.0
            if chunk_ratio < 0.3:
                # Small chunk: ensure at least 30% of chunk_size advance
                min_advance = max(1, int(self.chunk_size * 0.3))
            else:
                # Normal chunk: ensure at least 10% of chunk_size advance
                min_advance = max(1, int(self.chunk_size * 0.1))
            
            if new_pos <= current_pos:
                # If overlap causes no position advance, advance at least min_advance
                new_pos = current_pos + min_advance
                logger.debug(f"Overlap adjustment: current_pos={current_pos}, end_pos={end_pos}, overlap={overlap_amount}, chunk_size={len(chunk_text)}, adjusted new_pos={new_pos}")
            elif (new_pos - current_pos) < min_advance:
                # If advance is too small (e.g., small chunk causes large overlap), ensure at least min_advance
                new_pos = current_pos + min_advance
                logger.debug(f"Min advance adjustment: current_pos={current_pos}, calculated new_pos={end_pos - overlap_amount}, chunk_size={len(chunk_text)}, adjusted new_pos={new_pos}")
            
            # Ensure not exceeding text length
            if new_pos >= len(clean_section_text):
                break
                
            current_pos = new_pos
            chunk_index += 1
        
        logger.debug(f"Created {len(chunks)} chunks from section of {len(clean_section_text)} chars (heading_path: {heading_path})")
        if len(chunks) > 50:
            logger.warning(f"WARNING: Created {len(chunks)} chunks from section of only {len(clean_section_text)} chars! This seems excessive.")
            # Record chunk size information for diagnosis
            chunk_sizes = [len(c.text) for c in chunks]
            logger.warning(f"Chunk sizes: min={min(chunk_sizes)}, max={max(chunk_sizes)}, avg={sum(chunk_sizes)/len(chunk_sizes):.1f}")
            # Record details of first 5 chunks
            for i, c in enumerate(chunks[:5]):
                logger.warning(f"  Chunk {i}: size={len(c.text)}, start={c.location.start_char}, end={c.location.end_char}")
            # Check for duplicate chunks
            chunk_texts = [c.text[:50] for c in chunks[:10]]  # First 50 chars of first 10 chunks
            if len(chunk_texts) != len(set(chunk_texts)):
                logger.warning(f"  WARNING: Found duplicate chunks!")
        return chunks
    
    def _clean_page_markers(self, text: str) -> str:
        """
        Clean page markers and table HTML tags from text.
        
        Removes:
        - <page page="X" start_char="Y"> tags
        - </page> tags
        - ## Page X headings (Markdown format)
        - <table> and </table> tags (but keeps the Markdown table content)
        
        Preserves:
        - <img> tags (needed for rendering images in chatbot responses)
        
        Args:
            text: Text to clean
        
        Returns:
            Cleaned text
        """
        # Remove <page> and </page> tags
        cleaned = re.sub(r'<page[^>]*>|</page>', '', text, flags=re.IGNORECASE)
        
        # Remove ## Page X headings (handle various whitespace variants)
        cleaned = re.sub(r'^##\s+Page\s+\d+\s*$', '', cleaned, flags=re.MULTILINE | re.IGNORECASE)
        
        # Remove <table> and </table> tags, but keep the Markdown table content inside
        # This removes the HTML wrapper but preserves the Markdown table content
        # The table content is already in Markdown format (| col1 | col2 |), so the HTML tags are no longer needed
        cleaned = re.sub(r'<table[^>]*>', '', cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r'</table>', '', cleaned, flags=re.IGNORECASE)
        
        # Note: <img> tags are preserved - they are needed for rendering images
        # in chatbot responses when chunks containing images are retrieved
        
        # Clean up multiple consecutive newlines (3 or more)
        cleaned = re.sub(r'\n{3,}', '\n\n', cleaned)
        
        return cleaned.strip()
    
    def _protect_tags_in_chunk(self, chunk_text: str, full_text: str, start: int, proposed_end: int) -> str:
        """Protect HTML tags from being split."""
        # Check for unclosed tags
        if '<' in chunk_text and '>' not in chunk_text[-50:]:
            # Possibly in the middle of a tag, find tag end
            remaining = full_text[proposed_end:]
            tag_end = remaining.find('>')
            if tag_end != -1 and tag_end < 200:
                chunk_text = full_text[start:proposed_end + tag_end + 1]
        
        # Protect image tags
        if '<img' in chunk_text and '/>' not in chunk_text[-100:]:
            remaining = full_text[proposed_end:]
            img_end = remaining.find('/>')
            if img_end != -1 and img_end < 200:
                chunk_text = full_text[start:proposed_end + img_end + 2]
        
        # Protect table tags
        if '<table' in chunk_text and '</table>' not in chunk_text:
            remaining = full_text[proposed_end:]
            table_end = remaining.find('</table>')
            if table_end != -1 and table_end < 1000:
                chunk_text = full_text[start:proposed_end + table_end + 8]
        
        return chunk_text
    
    def _generate_chunk_id(self, document_id: str, chunk_index: int) -> str:
        """Generate unique chunk ID."""
        import hashlib
        content = f"{document_id}_{chunk_index}"
        return hashlib.md5(content.encode()).hexdigest()

