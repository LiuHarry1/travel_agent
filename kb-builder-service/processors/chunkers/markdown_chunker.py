"""Markdown-specific chunker."""
from typing import List
import re
from .base import BaseChunker
from models.document import Document
from models.chunk import Chunk, ChunkLocation


class MarkdownChunker(BaseChunker):
    """Markdown-specific chunker that respects heading hierarchy and protects code blocks."""
    
    def __init__(
        self,
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
        min_chunk_size: int = 100
    ):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.min_chunk_size = min_chunk_size
        # 标题模式
        self.heading_pattern = re.compile(r'^(#{1,6})\s+(.+)$', re.MULTILINE)
        # 代码块模式
        self.code_block_pattern = re.compile(r'```(\w+)?\n(.*?)```', re.DOTALL)
        # 图片和链接模式
        self.image_pattern = re.compile(r'!\[([^\]]*)\]\(([^)]+)\)')
        self.link_pattern = re.compile(r'\[([^\]]+)\]\(([^)]+)\)')
    
    def chunk(self, document: Document) -> List[Chunk]:
        """Split Markdown document into chunks, respecting heading hierarchy."""
        text = document.content
        
        if not text or len(text.strip()) == 0:
            return []
        
        chunks = []
        chunk_index = 0
        
        # 找到所有标题
        headings = list(self.heading_pattern.finditer(text))
        
        if not headings:
            # 没有标题，使用递归分片
            from .recursive import RecursiveChunker
            recursive_chunker = RecursiveChunker(
                chunk_size=self.chunk_size,
                chunk_overlap=self.chunk_overlap,
                min_chunk_size=self.min_chunk_size
            )
            return recursive_chunker.chunk(document)
        
        # 按标题层级分片
        for i, heading_match in enumerate(headings):
            heading_level = len(heading_match.group(1))
            heading_text = heading_match.group(2).strip()
            heading_start = heading_match.start()
            
            # 找到下一个同级或更高级标题的位置
            if i + 1 < len(headings):
                next_heading_start = headings[i + 1].start()
                # 如果下一个标题级别更高，继续包含
                next_level = len(headings[i + 1].group(1))
                if next_level > heading_level:
                    # 找到下一个同级或更高级标题
                    for j in range(i + 2, len(headings)):
                        j_level = len(headings[j].group(1))
                        if j_level <= heading_level:
                            next_heading_start = headings[j].start()
                            break
                section_end = next_heading_start
            else:
                section_end = len(text)
            
            section_text = text[heading_start:section_end].strip()
            
            # 构建标题路径
            heading_path = self._build_heading_path(headings, i)
            
            # 如果section太大，进一步分片
            if len(section_text) > self.chunk_size:
                section_chunks = self._chunk_within_section(
                    section_text,
                    document,
                    heading_path,
                    heading_start,
                    chunk_index
                )
                chunks.extend(section_chunks)
                chunk_index += len(section_chunks)
            else:
                # 整个section作为一个chunk
                # 提取代码块索引
                code_block_index = None
                code_blocks = list(self.code_block_pattern.finditer(section_text))
                if code_blocks:
                    code_block_index = 0  # 第一个代码块
                
                location = ChunkLocation(
                    start_char=heading_start,
                    end_char=section_end,
                    heading_path=heading_path,
                    code_block_index=code_block_index
                )
                
                chunk = Chunk(
                    text=section_text,
                    chunk_id=self._generate_chunk_id(document.source, chunk_index),
                    document_id=document.source,
                    chunk_index=chunk_index,
                    file_path=document.metadata.get("file_path") if document.metadata else None,
                    location=location,
                    metadata={
                        **document.metadata,
                        "chunk_size": len(section_text),
                        "start_pos": heading_start,
                        "end_pos": section_end
                    }
                )
                chunks.append(chunk)
                chunk_index += 1
        
        return chunks
    
    def _build_heading_path(self, headings: List[re.Match], current_idx: int) -> List[str]:
        """Build heading path from root to current heading."""
        path = []
        current_level = len(headings[current_idx].group(1))
        current_text = headings[current_idx].group(2).strip()
        
        # 向上查找父级标题
        for i in range(current_idx - 1, -1, -1):
            level = len(headings[i].group(1))
            if level < current_level:
                path.insert(0, headings[i].group(2).strip())
                current_level = level
                if level == 1:
                    break
        
        path.append(current_text)
        return path
    
    def _chunk_within_section(
        self,
        section_text: str,
        document: Document,
        heading_path: List[str],
        section_offset: int,
        start_chunk_index: int
    ) -> List[Chunk]:
        """Chunk within a section, protecting code blocks."""
        chunks = []
        chunk_index = start_chunk_index
        current_pos = 0
        
        # 找到所有代码块的位置
        code_blocks = list(self.code_block_pattern.finditer(section_text))
        code_block_indices = [(m.start(), m.end()) for m in code_blocks]
        
        while current_pos < len(section_text):
            end_pos = min(current_pos + self.chunk_size, len(section_text))
            chunk_text = section_text[current_pos:end_pos]
            
            # 检查是否在代码块中间
            in_code_block = False
            for cb_start, cb_end in code_block_indices:
                if cb_start < end_pos < cb_end:
                    # 在代码块中间，扩展到代码块结束
                    chunk_text = section_text[current_pos:cb_end]
                    end_pos = cb_end
                    in_code_block = True
                    break
            
            # 如果不在代码块中，尝试在句子边界分割
            if not in_code_block and end_pos < len(section_text):
                for sep in ['\n\n', '. ', '。', '！', '？', '\n']:
                    sep_pos = chunk_text.rfind(sep)
                    if sep_pos >= self.chunk_size * 0.5:
                        chunk_text = chunk_text[:sep_pos + len(sep)]
                        end_pos = current_pos + len(chunk_text)
                        break
            
            chunk_text = chunk_text.strip()
            if not chunk_text:
                current_pos = end_pos
                continue
            
            # 确定代码块索引
            code_block_index = None
            for idx, (cb_start, cb_end) in enumerate(code_block_indices):
                if cb_start >= current_pos and cb_end <= end_pos:
                    code_block_index = idx
                    break
            
            location = ChunkLocation(
                start_char=section_offset + current_pos,
                end_char=section_offset + end_pos,
                heading_path=heading_path.copy(),
                code_block_index=code_block_index
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
                    "start_pos": section_offset + current_pos,
                    "end_pos": section_offset + end_pos
                }
            )
            chunks.append(chunk)
            
            # 重叠
            overlap_amount = min(self.chunk_overlap, len(chunk_text))
            current_pos = max(current_pos + 1, end_pos - overlap_amount)
            chunk_index += 1
        
        return chunks
    
    def _generate_chunk_id(self, document_id: str, chunk_index: int) -> str:
        """Generate unique chunk ID."""
        import hashlib
        content = f"{document_id}_{chunk_index}"
        return hashlib.md5(content.encode()).hexdigest()

