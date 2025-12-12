"""PDF-specific chunker with table handling."""
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


class PDFChunker(BaseChunker):
    """PDF-specific chunker using RecursiveCharacterTextSplitter with table and page tracking."""
    
    def __init__(
        self,
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
        min_chunk_size: int = 100,
        encoding_name: str = "cl100k_base",
        table_max_rows_per_chunk: int = 5
    ):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.min_chunk_size = min_chunk_size
        self.encoding_name = encoding_name
        self.table_max_rows_per_chunk = table_max_rows_per_chunk
        
        # Create LangChain splitter with tiktoken
        self.splitter = create_tiktoken_splitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            encoding_name=encoding_name
        )
        
        # Create tiktoken encoder for token counting
        self.enc = tiktoken.get_encoding(encoding_name)
        
        # Patterns
        self.page_pattern = re.compile(r'<page\s+page="(\d+)"[^>]*>', re.IGNORECASE)
        self.table_pattern = re.compile(
            r'<table\s+index="(\d+)"\s+page="(\d+)"[^>]*>(.*?)</table>',
            re.DOTALL | re.IGNORECASE
        )
    
    def chunk(self, document: Document) -> List[Chunk]:
        """Split PDF document into chunks, handling tables separately."""
        text = document.content
        
        if not text or len(text.strip()) == 0:
            return []
        
        # Step 1: Extract tables and replace with placeholders
        text_with_placeholders, table_blocks = self._extract_tables(text)
        
        # Step 2: Use RecursiveCharacterTextSplitter for non-table text
        text_chunks = self.splitter.split_text(text_with_placeholders)
        
        # Step 3: Build page position map
        page_map = self._build_page_map(text)
        
        # Step 4: Convert to Chunk objects
        chunks = []
        chunk_index = 0
        current_pos = 0
        skip_next = False  # Flag to skip next chunk if merged
        
        for idx, chunk_text in enumerate(text_chunks):
            # Skip if this chunk was merged with previous one
            if skip_next:
                skip_next = False
                continue
            
            chunk_text = chunk_text.strip()
            if not chunk_text:
                continue
            
            # Check if this chunk contains a table placeholder
            placeholder_match = re.search(r'<TABLE_PLACEHOLDER_(\d+)>', chunk_text)
            
            if placeholder_match:
                # This is a table chunk
                table_id = int(placeholder_match.group(1))
                table_block = table_blocks.get(table_id)
                
                if table_block:
                    # Process table (may split large tables)
                    table_chunks = self._process_table(
                        table_block,
                        document,
                        chunk_index,
                        page_map
                    )
                    chunks.extend(table_chunks)
                    chunk_index += len(table_chunks)
                continue
            
            # Regular text chunk
            # Clean page markers first to check if chunk becomes empty
            cleaned_text = self._clean_page_markers(chunk_text)
            
            # Skip if cleaned text is empty
            if not cleaned_text or not cleaned_text.strip():
                continue
            
            # Check minimum chunk size (in tokens)
            token_count = len(self.enc.encode(cleaned_text))
            if token_count < self.min_chunk_size:
                # Try to merge with next chunk if available
                if idx + 1 < len(text_chunks):
                    next_chunk_text = text_chunks[idx + 1].strip()
                    if next_chunk_text:
                        # Check if next chunk is not a table placeholder
                        if not re.search(r'<TABLE_PLACEHOLDER_(\d+)>', next_chunk_text):
                            next_cleaned = self._clean_page_markers(next_chunk_text)
                            if next_cleaned and next_cleaned.strip():
                                merged_text = cleaned_text + "\n\n" + next_cleaned
                                merged_token_count = len(self.enc.encode(merged_text))
                                # Only merge if merged chunk is reasonable size
                                if merged_token_count <= self.chunk_size * 1.5:
                                    cleaned_text = merged_text
                                    # Mark next chunk to skip
                                    skip_next = True
                else:
                    # Last chunk: always include it even if small to avoid losing content
                    # Only skip if it's completely empty (no actual content)
                    if token_count == 0:
                        logger.warning(f"Skipping empty last chunk at index {chunk_index}")
                        continue
                    else:
                        # Include small last chunk to preserve content
                        logger.debug(f"Including small last chunk (tokens: {token_count}, min: {self.min_chunk_size})")
            
            # Find position in original text (before cleaning)
            start_pos = text.find(chunk_text, current_pos)
            if start_pos == -1:
                start_pos = current_pos
            end_pos = start_pos + len(chunk_text)
            current_pos = end_pos
            
            # Find page number
            page_number = self._find_page_number(start_pos, page_map)
            
            # Create chunk with cleaned text
            chunk = self._create_text_chunk(
                document,
                cleaned_text,  # Use cleaned text directly
                chunk_index,
                start_pos,
                end_pos,
                page_number
            )
            chunks.append(chunk)
            chunk_index += 1
        
        logger.info(f"Created {len(chunks)} chunks from PDF ({sum(1 for c in chunks if c.location and c.location.table_index is not None)} table chunks)")
        return chunks
    
    def _extract_tables(self, text: str) -> Tuple[str, Dict[int, Dict]]:
        """
        Extract tables from text and replace with placeholders.
        
        Returns:
            (text_with_placeholders, table_blocks_dict)
        """
        table_blocks = {}
        text_with_placeholders = text
        table_id = 0
        
        for match in self.table_pattern.finditer(text):
            table_index = int(match.group(1))
            table_page = int(match.group(2))
            table_content = match.group(3).strip()
            
            # Store table block
            table_blocks[table_id] = {
                'index': table_index,
                'page': table_page,
                'content': table_content,
                'start_pos': match.start(),
                'end_pos': match.end()
            }
            
            # Replace with placeholder
            placeholder = f'<TABLE_PLACEHOLDER_{table_id}>'
            text_with_placeholders = text_with_placeholders.replace(
                match.group(0),
                placeholder,
                1
            )
            
            table_id += 1
        
        return text_with_placeholders, table_blocks
    
    def _process_table(
        self,
        table_block: Dict,
        document: Document,
        start_chunk_index: int,
        page_map: List[Tuple[int, int]]
    ) -> List[Chunk]:
        """
        Process a table block into chunks.
        
        For small tables: one chunk
        For large tables: split by rows (3-5 rows per chunk)
        """
        table_content = table_block['content']
        table_index = table_block['index']
        table_page = table_block['page']
        start_pos = table_block['start_pos']
        end_pos = table_block['end_pos']
        
        # Parse table rows
        table_lines = [line.strip() for line in table_content.split('\n') if line.strip()]
        
        # Check if table is small enough to be one chunk
        table_token_count = len(self.enc.encode(table_content))
        
        if table_token_count <= self.chunk_size:
            # Small table: one chunk
            chunk = self._create_table_chunk(
                document,
                table_content,
                start_chunk_index,
                table_index,
                table_page,
                start_pos,
                end_pos,
                row_range=(0, len(table_lines) - 1) if table_lines else None
            )
            return [chunk]
        else:
            # Large table: split by rows
            chunks = []
            chunk_index = start_chunk_index
            
            # Identify header (first line is usually header, second is separator)
            header_lines = []
            data_lines = []
            
            if len(table_lines) >= 2:
                # Check if second line is a separator
                if re.match(r'^\|[\s\-:]+\|', table_lines[1]):
                    header_lines = [table_lines[0], table_lines[1]]
                    data_lines = table_lines[2:]
                else:
                    # No separator, treat first line as header
                    header_lines = [table_lines[0]]
                    data_lines = table_lines[1:]
            else:
                data_lines = table_lines
            
            # Split data rows into groups
            row_groups = []
            current_group = []
            
            for line in data_lines:
                current_group.append(line)
                
                # If group reaches max size, save it
                if len(current_group) >= self.table_max_rows_per_chunk:
                    row_groups.append(current_group)
                    current_group = []
            
            # Add remaining group
            if current_group:
                row_groups.append(current_group)
            
            # Create chunks for each row group (each includes header)
            data_row_index = 0
            for group in row_groups:
                # Combine header and data rows
                group_with_header = header_lines + group
                group_text = '\n'.join(group_with_header)
                
                # Calculate row range (data rows only, 0-indexed)
                num_data_rows = len(group)
                row_start = data_row_index
                row_end = data_row_index + num_data_rows - 1
                
                # Calculate approximate position for this group
                total_data_rows = len(data_lines)
                if total_data_rows > 0:
                    progress = data_row_index / total_data_rows
                    group_start_pos = start_pos + int(progress * (end_pos - start_pos))
                    progress_end = (data_row_index + num_data_rows) / total_data_rows
                    group_end_pos = start_pos + int(progress_end * (end_pos - start_pos))
                else:
                    group_start_pos = start_pos
                    group_end_pos = end_pos
                
                chunk = self._create_table_chunk(
                    document,
                    group_text,
                    chunk_index,
                    table_index,
                    table_page,
                    group_start_pos,
                    group_end_pos,
                    row_range=(row_start, row_end) if num_data_rows > 0 else None
                )
                chunks.append(chunk)
                
                data_row_index += num_data_rows
                chunk_index += 1
            
            return chunks
    
    def _create_table_chunk(
        self,
        document: Document,
        table_text: str,
        chunk_index: int,
        table_index: int,
        page_number: int,
        start_pos: int,
        end_pos: int,
        row_range: Optional[Tuple[int, int]] = None
    ) -> Chunk:
        """Create a chunk for a table."""
        # Clean page markers from table text (though tables shouldn't have them)
        cleaned_text = self._clean_page_markers(table_text)
        
        chunk_id = self._generate_chunk_id(document.source, chunk_index)
        file_path = document.metadata.get("file_path") if document.metadata else None
        
        # Create location with table info
        location = ChunkLocation(
            start_char=start_pos,
            end_char=end_pos,
            page_number=page_number,
            table_index=table_index
        )
        
        # Build metadata
        metadata = {
            **document.metadata,
            "chunk_size": len(cleaned_text),
            "start_pos": start_pos,
            "end_pos": end_pos,
            "page_number": page_number,
            "table_index": table_index,
            "content_type": "table"
        }
        
        if row_range:
            metadata["table_row_range"] = f"{row_range[0]}-{row_range[1]}"
        
        return Chunk(
            text=cleaned_text,
            chunk_id=chunk_id,
            document_id=document.source,
            chunk_index=chunk_index,
            file_path=file_path,
            location=location,
            metadata=metadata
        )
    
    def _clean_page_markers(self, text: str) -> str:
        """
        Clean page markers from text.
        
        Removes:
        - <page page="X" start_char="Y"> tags
        - </page> tags
        - ## Page X headings (Markdown format)
        
        Args:
            text: Text to clean
        
        Returns:
            Cleaned text
        """
        # Remove <page> and </page> tags
        cleaned = re.sub(r'<page[^>]*>|</page>', '', text, flags=re.IGNORECASE)
        
        # Remove ## Page X headings (handle various whitespace variants)
        cleaned = re.sub(r'^##\s+Page\s+\d+\s*$', '', cleaned, flags=re.MULTILINE | re.IGNORECASE)
        
        # Clean up multiple consecutive newlines (3 or more)
        cleaned = re.sub(r'\n{3,}', '\n\n', cleaned)
        
        return cleaned.strip()
    
    def _create_text_chunk(
        self,
        document: Document,
        chunk_text: str,  # Already cleaned text
        chunk_index: int,
        start_pos: int,
        end_pos: int,
        page_number: Optional[int]
    ) -> Chunk:
        """Create a chunk for regular text."""
        # Note: chunk_text is already cleaned before calling this method
        chunk_id = self._generate_chunk_id(document.source, chunk_index)
        file_path = document.metadata.get("file_path") if document.metadata else None
        
        location = ChunkLocation(
            start_char=start_pos,
            end_char=end_pos,
            page_number=page_number
        )
        
        return Chunk(
            text=chunk_text,  # Use cleaned text directly
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
                "page_number": page_number,
                "content_type": "text"
            }
        )
    
    def _build_page_map(self, text: str) -> List[Tuple[int, int]]:
        """
        Build a list of (position, page_number) tuples sorted by position.
        
        Returns:
            List of (position, page_number) tuples
        """
        page_map = []
        for match in self.page_pattern.finditer(text):
            page_num = int(match.group(1))
            position = match.start()
            page_map.append((position, page_num))
        
        # Sort by position
        page_map.sort(key=lambda x: x[0])
        return page_map
    
    def _find_page_number(self, position: int, page_map: List[Tuple[int, int]]) -> Optional[int]:
        """
        Find the page number for a given position.
        
        Args:
            position: Character position in text
            page_map: List of (position, page_number) tuples sorted by position
        
        Returns:
            Page number or None if not found
        """
        if not page_map:
            return None
        
        # Binary search for the page that contains this position
        # Find the last page marker that is <= position
        page_number = None
        for pos, page_num in page_map:
            if pos <= position:
                page_number = page_num
            else:
                break
        
        return page_number
    
    def _generate_chunk_id(self, document_id: str, chunk_index: int) -> str:
        """Generate unique chunk ID."""
        content = f"{document_id}_{chunk_index}"
        return hashlib.md5(content.encode()).hexdigest()
