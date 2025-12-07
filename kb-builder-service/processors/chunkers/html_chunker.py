"""HTML-specific chunker."""
from typing import List
import re
from .base import BaseChunker
from models.document import Document
from models.chunk import Chunk, ChunkLocation


class HTMLChunker(BaseChunker):
    """HTML-specific chunker that respects heading hierarchy and protects HTML tags."""
    
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
        # HTML标签模式
        self.html_tag_pattern = re.compile(r'<[^>]+>')
        # 需要保护的标签
        self.protected_tags = ['img', 'a', 'table', 'ul', 'ol', 'li', 'div', 'span', 'p']
    
    def chunk(self, document: Document) -> List[Chunk]:
        """Split HTML document into chunks, respecting heading hierarchy."""
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
                location = ChunkLocation(
                    start_char=heading_start,
                    end_char=section_end,
                    heading_path=heading_path
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
        """Chunk within a section, protecting HTML tags."""
        chunks = []
        chunk_index = start_chunk_index
        current_pos = 0
        
        while current_pos < len(section_text):
            end_pos = min(current_pos + self.chunk_size, len(section_text))
            chunk_text = section_text[current_pos:end_pos]
            
            # 保护HTML标签
            if end_pos < len(section_text):
                chunk_text = self._protect_html_tags(chunk_text, section_text, current_pos, end_pos)
                end_pos = current_pos + len(chunk_text)
            
            chunk_text = chunk_text.strip()
            if not chunk_text:
                current_pos = end_pos
                continue
            
            location = ChunkLocation(
                start_char=section_offset + current_pos,
                end_char=section_offset + end_pos,
                heading_path=heading_path.copy()
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
    
    def _protect_html_tags(self, chunk_text: str, full_text: str, start: int, proposed_end: int) -> str:
        """Protect HTML tags from being split."""
        # 检查未闭合的标签
        for tag in self.protected_tags:
            tag_pattern = f'<{tag}[^>]*>'
            if re.search(tag_pattern, chunk_text, re.IGNORECASE):
                # 检查是否有闭合标签
                closing_tag = f'</{tag}>'
                if closing_tag not in chunk_text:
                    # 查找闭合标签
                    remaining = full_text[proposed_end:]
                    closing_pos = remaining.find(closing_tag)
                    if closing_pos != -1 and closing_pos < 500:
                        chunk_text = full_text[start:proposed_end + closing_pos + len(closing_tag)]
                        break
        
        # 检查自闭合标签（如<img />）
        if '<img' in chunk_text and '/>' not in chunk_text[-100:]:
            remaining = full_text[proposed_end:]
            img_end = remaining.find('/>')
            if img_end != -1 and img_end < 200:
                chunk_text = full_text[start:proposed_end + img_end + 2]
        
        return chunk_text
    
    def _generate_chunk_id(self, document_id: str, chunk_index: int) -> str:
        """Generate unique chunk ID."""
        import hashlib
        content = f"{document_id}_{chunk_index}"
        return hashlib.md5(content.encode()).hexdigest()

