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
        # 页面标记模式
        self.page_pattern = re.compile(r'<page\s+page="(\d+)"[^>]*>', re.IGNORECASE)
        self.page_close_pattern = re.compile(r'</page>', re.IGNORECASE)
        # 图片标签模式
        self.img_pattern = re.compile(r'<img[^>]+>', re.IGNORECASE)
        # 表格标记模式
        self.table_pattern = re.compile(r'<table[^>]*>.*?</table>', re.DOTALL | re.IGNORECASE)
    
    def chunk(self, document: Document) -> List[Chunk]:
        """Split PDF document into chunks, respecting heading hierarchy or page boundaries."""
        text = document.content
        
        if not text or len(text.strip()) == 0:
            return []
        
        chunks = []
        chunk_index = 0
        
        # 尝试使用标题信息进行分块
        # 检查是否有PDF标题信息
        pdf_headings = None
        if document.structure and document.structure.pdf_headings:
            pdf_headings = document.structure.pdf_headings
        
        # 查找Markdown格式的标题（在_load_pdf中已经插入）
        heading_pattern = re.compile(r'^(#{1,6})\s+(.+)$', re.MULTILINE)
        headings = list(heading_pattern.finditer(text))
        
        # 如果有标题，优先使用标题分块
        if headings:
            logger.info(f"Using heading-based chunking for PDF with {len(headings)} headings")
            return self._chunk_by_headings(text, document, headings, chunk_index)
        
        # 如果没有标题，回退到页面分块
        logger.info("No headings detected, falling back to page-based chunking")
        return self._chunk_by_pages(text, document)
    
    def _chunk_by_pages(self, text: str, document: Document) -> List[Chunk]:
        """按页面分块（原有逻辑）"""
        chunks = []
        chunk_index = 0
        
        # 找到所有页面标记
        page_matches = list(self.page_pattern.finditer(text))
        
        if not page_matches:
            # 如果没有页面标记，使用递归分片
            from .recursive import RecursiveChunker
            recursive_chunker = RecursiveChunker(
                chunk_size=self.chunk_size,
                chunk_overlap=self.chunk_overlap,
                min_chunk_size=self.min_chunk_size
            )
            return recursive_chunker.chunk(document)
        
        # 按页面分片
        for i, page_match in enumerate(page_matches):
            page_num = int(page_match.group(1))
            page_start = page_match.start()
            
            # 找到页面结束位置
            if i + 1 < len(page_matches):
                page_end = page_matches[i + 1].start()
            else:
                # 最后一个页面，找到 </page> 标签
                close_match = self.page_close_pattern.search(text, page_start)
                page_end = close_match.end() if close_match else len(text)
            
            page_text = text[page_start:page_end]
            
            # 在页面内进一步分片（如果需要）
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
        """按标题层级分块（参考markdown_chunker的实现）"""
        chunks = []
        chunk_index = start_chunk_index
        
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
            
            # 提取页面信息（从section_text中的<page>标签）
            page_num = None
            page_match = self.page_pattern.search(section_text)
            if page_match:
                page_num = int(page_match.group(1))
            
            # 如果section太大，进一步分片
            if len(section_text) > self.chunk_size:
                section_chunks = self._chunk_within_section(
                    section_text,
                    document,
                    heading_path,
                    heading_start,
                    chunk_index,
                    page_num
                )
                chunks.extend(section_chunks)
                chunk_index += len(section_chunks)
            else:
                # 整个section作为一个chunk
                location = ChunkLocation(
                    start_char=heading_start,
                    end_char=section_end,
                    heading_path=heading_path,
                    page_number=page_num
                )
                
                # 提取图片信息
                img_match = self.img_pattern.search(section_text)
                if img_match:
                    img_src_match = re.search(r'src="([^"]+)"', img_match.group(0))
                    if img_src_match:
                        location.image_url = img_src_match.group(1)
                    img_idx_match = re.search(r'image_index="(\d+)"', img_match.group(0))
                    if img_idx_match:
                        location.image_index = int(img_idx_match.group(1))
                
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
                        "end_pos": section_end,
                        "page_number": page_num
                    }
                )
                chunks.append(chunk)
                chunk_index += 1
        
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
        
        # 移除页面标签，但保留内容
        clean_text = re.sub(r'<page[^>]*>|</page>', '', page_text, flags=re.IGNORECASE)
        clean_text = clean_text.strip()
        
        if not clean_text:
            return []
        
        # 如果页面内容小于chunk_size，直接作为一个chunk
        if len(clean_text) <= self.chunk_size:
            location = ChunkLocation(
                start_char=page_offset + current_pos,
                end_char=page_offset + len(page_text),
                page_number=page_num
            )
            # 提取图片信息
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
        
        # 页面内容较大，需要进一步分片
        # 使用改进的递归分片，但保护图片和表格
        while current_pos < len(clean_text):
            end_pos = min(current_pos + self.chunk_size, len(clean_text))
            chunk_text = clean_text[current_pos:end_pos]
            
            # 如果不在文本末尾，尝试在安全位置分割
            if end_pos < len(clean_text):
                # 保护图片标签
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
            
            # 提取图片信息
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
            
            # 计算下一个位置（带重叠）
            overlap_amount = min(self.chunk_overlap, len(chunk_text))
            current_pos = max(current_pos + 1, end_pos - overlap_amount)
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
        start_chunk_index: int,
        page_num: Optional[int] = None
    ) -> List[Chunk]:
        """Chunk within a section, protecting images and tables."""
        chunks = []
        chunk_index = start_chunk_index
        current_pos = 0
        
        # 移除页面标签，但保留内容用于分块
        clean_section_text = re.sub(r'<page[^>]*>|</page>', '', section_text, flags=re.IGNORECASE)
        clean_section_text = clean_section_text.strip()
        
        while current_pos < len(clean_section_text):
            end_pos = min(current_pos + self.chunk_size, len(clean_section_text))
            chunk_text = clean_section_text[current_pos:end_pos]
            
            # 如果不在文本末尾，尝试在安全位置分割
            if end_pos < len(clean_section_text):
                # 保护图片和表格标签
                chunk_text = self._protect_tags_in_chunk(chunk_text, clean_section_text, current_pos, end_pos)
                end_pos = current_pos + len(chunk_text)
            
            chunk_text = chunk_text.strip()
            if not chunk_text:
                current_pos = end_pos
                continue
            
            # 检查最小chunk大小
            if len(chunk_text) < self.min_chunk_size and end_pos < len(clean_section_text):
                # 尝试扩展
                extended_end = min(current_pos + self.chunk_size * 1.5, len(clean_section_text))
                extended_text = clean_section_text[current_pos:extended_end]
                extended_text = self._protect_tags_in_chunk(extended_text, clean_section_text, current_pos, extended_end)
                if len(extended_text.strip()) >= self.min_chunk_size:
                    chunk_text = extended_text.strip()
                    end_pos = current_pos + len(extended_text)
            
            location = ChunkLocation(
                start_char=section_offset + current_pos,
                end_char=section_offset + end_pos,
                heading_path=heading_path.copy(),
                page_number=page_num
            )
            
            # 提取图片信息
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
            
            # 重叠
            overlap_amount = min(self.chunk_overlap, len(chunk_text))
            current_pos = max(current_pos + 1, end_pos - overlap_amount)
            chunk_index += 1
        
        return chunks
    
    def _protect_tags_in_chunk(self, chunk_text: str, full_text: str, start: int, proposed_end: int) -> str:
        """Protect HTML tags from being split."""
        # 检查是否有未闭合的标签
        if '<' in chunk_text and '>' not in chunk_text[-50:]:
            # 可能在标签中间，找到标签结束
            remaining = full_text[proposed_end:]
            tag_end = remaining.find('>')
            if tag_end != -1 and tag_end < 200:
                chunk_text = full_text[start:proposed_end + tag_end + 1]
        
        # 保护图片标签
        if '<img' in chunk_text and '/>' not in chunk_text[-100:]:
            remaining = full_text[proposed_end:]
            img_end = remaining.find('/>')
            if img_end != -1 and img_end < 200:
                chunk_text = full_text[start:proposed_end + img_end + 2]
        
        # 保护表格标签
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

