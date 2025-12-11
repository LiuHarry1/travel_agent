"""HTML-specific chunker using RecursiveCharacterTextSplitter with table handling."""
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


class HTMLChunker(BaseChunker):
    """HTML-specific chunker using RecursiveCharacterTextSplitter with table and page tracking."""
    
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
        
        # Table pattern: Markdown table format (| col1 | col2 |)
        # Matches table with header separator line
        self.table_pattern = re.compile(
            r'(\|[^\n]+\|\n\|[\s\-:]+\|\n(?:\|[^\n]+\|\n?)+)',
            re.MULTILINE
        )
    
    def chunk(self, document: Document) -> List[Chunk]:
        """Split HTML document into chunks, handling tables separately."""
        text = document.content
        
        if not text or len(text.strip()) == 0:
            return []
        
        # Step 1: Extract tables and replace with placeholders
        text_with_placeholders, table_blocks = self._extract_tables(text)
        
        # Step 2: Use RecursiveCharacterTextSplitter for non-table text
        text_chunks = self.splitter.split_text(text_with_placeholders)
        
        # Step 3: Convert to Chunk objects
        chunks = []
        chunk_index = 0
        current_pos = 0
        
        for chunk_text in text_chunks:
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
                        chunk_index
                    )
                    chunks.extend(table_chunks)
                    chunk_index += len(table_chunks)
                continue
            
            # Regular text chunk
            # Remove any placeholders from chunk_text for position finding
            chunk_text_for_search = re.sub(r'<TABLE_PLACEHOLDER_\d+>', '', chunk_text)
            # Find position in original text
            start_pos = text.find(chunk_text_for_search, current_pos)
            if start_pos == -1:
                # Try finding in text_with_placeholders and map back
                placeholder_pos = text_with_placeholders.find(chunk_text, current_pos)
                if placeholder_pos != -1:
                    # Approximate mapping: placeholder is shorter than table, so position should be close
                    start_pos = placeholder_pos
                else:
                    start_pos = current_pos
            end_pos = start_pos + len(chunk_text_for_search)
            current_pos = end_pos
            
            # Create chunk
            chunk = self._create_text_chunk(
                document,
                chunk_text,
                chunk_index,
                start_pos,
                end_pos
            )
            chunks.append(chunk)
            chunk_index += 1
        
        logger.info(f"Created {len(chunks)} chunks from HTML ({sum(1 for c in chunks if c.location and c.location.table_index is not None)} table chunks)")
        return chunks
    
    def _extract_tables(self, text: str) -> Tuple[str, Dict[int, Dict]]:
        """
        Extract Markdown tables from text and replace with placeholders.
        
        Returns:
            (text_with_placeholders, table_blocks_dict)
        """
        table_blocks = {}
        text_with_placeholders = text
        table_id = 0
        
        for match in self.table_pattern.finditer(text):
            table_content = match.group(1).strip()
            
            # Store table block
            table_blocks[table_id] = {
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
        start_chunk_index: int
    ) -> List[Chunk]:
        """
        Process a table block into chunks.
        
        For small tables: one chunk
        For large tables: split by rows (3-5 rows per chunk)
        """
        table_content = table_block['content']
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
                0,  # table_index
                start_pos,
                end_pos,
                row_range=(0, len(table_lines) - 2) if len(table_lines) >= 2 else None  # Exclude separator line
            )
            return [chunk]
        else:
            # Large table: split by rows
            chunks = []
            chunk_index = start_chunk_index
            
            # Identify header (first line is header, second is separator)
            header_lines = []
            data_lines = []
            
            if len(table_lines) >= 2:
                header_lines = [table_lines[0], table_lines[1]]  # Header and separator
                data_lines = table_lines[2:]
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
                    0,  # table_index
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
        start_pos: int,
        end_pos: int,
        row_range: Optional[Tuple[int, int]] = None
    ) -> Chunk:
        """Create a chunk for a table."""
        chunk_id = self._generate_chunk_id(document.source, chunk_index)
        file_path = document.metadata.get("file_path") if document.metadata else None
        
        # Create location with table info
        location = ChunkLocation(
            start_char=start_pos,
            end_char=end_pos,
            table_index=table_index
        )
        
        # Build metadata
        metadata = {
            **document.metadata,
            "chunk_size": len(table_text),
            "start_pos": start_pos,
            "end_pos": end_pos,
            "table_index": table_index,
            "content_type": "table"
        }
        
        if row_range:
            metadata["table_row_range"] = f"{row_range[0]}-{row_range[1]}"
        
        return Chunk(
            text=table_text,
            chunk_id=chunk_id,
            document_id=document.source,
            chunk_index=chunk_index,
            file_path=file_path,
            location=location,
            metadata=metadata
        )
    
    def _create_text_chunk(
        self,
        document: Document,
        chunk_text: str,
        chunk_index: int,
        start_pos: int,
        end_pos: int
    ) -> Chunk:
        """Create a chunk for regular text."""
        chunk_id = self._generate_chunk_id(document.source, chunk_index)
        file_path = document.metadata.get("file_path") if document.metadata else None
        
        location = ChunkLocation(
            start_char=start_pos,
            end_char=end_pos
        )
        
        return Chunk(
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
    
    def _generate_chunk_id(self, document_id: str, chunk_index: int) -> str:
        """Generate unique chunk ID."""
        content = f"{document_id}_{chunk_index}"
        return hashlib.md5(content.encode()).hexdigest()
