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
        all_headings = list(heading_pattern.finditer(text))
        
        # 过滤掉"Page X"这样的伪标题
        headings = []
        page_heading_pattern = re.compile(r'^Page\s+\d+$', re.IGNORECASE)
        for heading_match in all_headings:
            heading_text = heading_match.group(2).strip()
            # 跳过"Page X"格式的标题
            if not page_heading_pattern.match(heading_text):
                headings.append(heading_match)
        
        # 如果有标题，优先使用标题分块
        if headings:
            logger.info(f"Using heading-based chunking for PDF with {len(headings)} headings (filtered {len(all_headings) - len(headings)} page markers)")
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
        
        logger.info(f"Starting heading-based chunking with {len(headings)} headings")
        
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
            
            # 提取页面信息（从section_text中的<page>标签，在清理前提取）
            page_num = None
            page_match = self.page_pattern.search(section_text)
            if page_match:
                page_num = int(page_match.group(1))
            
            # 清理页面标记
            clean_section_text = self._clean_page_markers(section_text)
            
            # 跳过太小的section（小于min_chunk_size）
            if len(clean_section_text.strip()) < self.min_chunk_size:
                # 尝试合并到前一个chunk（如果存在）
                if chunks:
                    last_chunk = chunks[-1]
                    # 合并文本
                    merged_text = last_chunk.text + "\n\n" + clean_section_text
                    if len(merged_text) <= self.chunk_size * 1.5:  # 允许适度超出
                        last_chunk.text = merged_text
                        last_chunk.location.end_char = section_end
                        last_chunk.metadata["chunk_size"] = len(merged_text)
                        last_chunk.metadata["end_pos"] = section_end
                        continue
                # 如果无法合并，跳过太小的section
                continue
            
            # 如果section太大，进一步分片
            if len(clean_section_text) > self.chunk_size:
                logger.debug(f"Section too large ({len(clean_section_text)} chars), splitting. heading_path: {heading_path}")
                section_chunks = self._chunk_within_section(
                    clean_section_text,  # 使用清理后的文本，避免重复清理和位置计算错误
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
        
        # 清理页面标记
        clean_text = self._clean_page_markers(page_text)
        
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
        
        # 过滤"Page X"伪标题的模式
        page_heading_pattern = re.compile(r'^Page\s+\d+$', re.IGNORECASE)
        
        # 向上查找父级标题
        for i in range(current_idx - 1, -1, -1):
            level = len(headings[i].group(1))
            heading_text = headings[i].group(2).strip()
            # 跳过"Page X"格式的伪标题
            if page_heading_pattern.match(heading_text):
                continue
            if level < current_level:
                path.insert(0, heading_text)
                current_level = level
                if level == 1:
                    break
        
        # 确保当前标题也不是"Page X"
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
            
            # 提取图片信息
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
            
            # 防止无限循环：确保end_pos至少比current_pos大1
            if end_pos <= current_pos:
                end_pos = min(current_pos + 1, len(clean_section_text))
            
            chunk_text = clean_section_text[current_pos:end_pos]
            
            # 如果不在文本末尾，尝试在安全位置分割
            if end_pos < len(clean_section_text):
                # 保护图片和表格标签
                protected_chunk = self._protect_tags_in_chunk(chunk_text, clean_section_text, current_pos, end_pos)
                # 只有在protected_chunk确实更长时才使用它
                if len(protected_chunk) > len(chunk_text):
                    chunk_text = protected_chunk
                    end_pos = current_pos + len(chunk_text)
                # 再次确保end_pos > current_pos
                if end_pos <= current_pos:
                    end_pos = current_pos + 1
                    chunk_text = clean_section_text[current_pos:end_pos]
            
            # 记录strip前的end_pos，用于后续计算
            original_end_pos = end_pos
            chunk_text = chunk_text.strip()
            
            # 如果strip后chunk_text变小很多，需要调整end_pos
            # 但要注意：strip只是移除首尾空白，不应该改变end_pos
            # 问题可能是：如果chunk_text主要是空白，strip后变得很小
            # 但end_pos是基于原始chunk_text计算的，所以应该保持不变
            
            if not chunk_text:
                # 如果strip后为空，说明这段主要是空白，跳过
                # 确保至少前进1个字符，防止无限循环
                current_pos = max(current_pos + 1, end_pos)
                if current_pos >= len(clean_section_text):
                    break
                continue
            
            # 检查最小chunk大小
            if len(chunk_text) < self.min_chunk_size:
                if end_pos < len(clean_section_text):
                    # 尝试扩展：扩展到chunk_size的1.5倍
                    extended_end = min(current_pos + int(self.chunk_size * 1.5), len(clean_section_text))
                    extended_text = clean_section_text[current_pos:extended_end]
                    extended_text = self._protect_tags_in_chunk(extended_text, clean_section_text, current_pos, extended_end)
                    extended_text_stripped = extended_text.strip()
                    if len(extended_text_stripped) >= self.min_chunk_size:
                        chunk_text = extended_text_stripped
                        end_pos = current_pos + len(extended_text)
                    else:
                        # 无法扩展到最小大小，尝试合并到前一个chunk
                        if chunks and chunk_index > start_chunk_index:
                            last_chunk = chunks[-1]
                            merged_text = last_chunk.text + "\n\n" + chunk_text
                            if len(merged_text) <= int(self.chunk_size * 1.5):
                                last_chunk.text = merged_text
                                last_chunk.location.end_char = section_offset + end_pos
                                last_chunk.metadata["chunk_size"] = len(merged_text)
                                last_chunk.metadata["end_pos"] = section_offset + end_pos
                                # 移动到下一个位置（考虑overlap，但确保至少前进chunk_size的20%）
                                overlap_amount = min(self.chunk_overlap, len(merged_text))
                                min_advance = max(1, int(self.chunk_size * 0.2))
                                current_pos = max(current_pos + min_advance, end_pos - overlap_amount)
                                if current_pos >= len(clean_section_text):
                                    break
                                continue
                        # 如果无法合并，跳过太小的chunk
                        # 直接跳到下一个合理的分割点（至少前进chunk_size的50%）
                        # 这样可以避免创建太多很小的chunks
                        skip_to = min(current_pos + max(self.chunk_size // 2, self.min_chunk_size * 2), len(clean_section_text))
                        current_pos = skip_to
                        if current_pos >= len(clean_section_text):
                            break
                        continue
                else:
                    # 已到文本末尾，尝试合并到前一个chunk
                    if chunks and chunk_index > start_chunk_index:
                        last_chunk = chunks[-1]
                        merged_text = last_chunk.text + "\n\n" + chunk_text
                        last_chunk.text = merged_text
                        last_chunk.location.end_char = section_offset + end_pos
                        last_chunk.metadata["chunk_size"] = len(merged_text)
                        last_chunk.metadata["end_pos"] = section_offset + end_pos
                        # 确保至少前进1个字符，防止无限循环
                        current_pos = max(current_pos + 1, end_pos)
                        continue
                    # 如果无法合并且是最后一个chunk，仍然添加（避免丢失内容）
                    # 但记录警告
                    if len(chunk_text) < self.min_chunk_size:
                        logger.warning(f"Creating small chunk ({len(chunk_text)} chars) at end of section")
            
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
            
            # 重叠：计算下一个chunk的起始位置
            # 正常情况下，下一个chunk应该从 end_pos - overlap_amount 开始
            overlap_amount = min(self.chunk_overlap, len(chunk_text))
            new_pos = end_pos - overlap_amount
            
            # 确保位置确实前进了
            # 如果chunk很小（小于chunk_size的30%），overlap可能导致位置几乎不前进
            # 需要确保至少前进chunk_size的20%，避免创建太多小chunks
            chunk_ratio = len(chunk_text) / self.chunk_size if self.chunk_size > 0 else 1.0
            if chunk_ratio < 0.3:
                # 小chunk：确保至少前进chunk_size的30%
                min_advance = max(1, int(self.chunk_size * 0.3))
            else:
                # 正常chunk：确保至少前进chunk_size的10%
                min_advance = max(1, int(self.chunk_size * 0.1))
            
            if new_pos <= current_pos:
                # 如果overlap导致位置没有前进，至少前进min_advance
                new_pos = current_pos + min_advance
                logger.debug(f"Overlap adjustment: current_pos={current_pos}, end_pos={end_pos}, overlap={overlap_amount}, chunk_size={len(chunk_text)}, adjusted new_pos={new_pos}")
            elif (new_pos - current_pos) < min_advance:
                # 如果前进太少（比如chunk很小导致overlap很大），确保至少前进min_advance
                new_pos = current_pos + min_advance
                logger.debug(f"Min advance adjustment: current_pos={current_pos}, calculated new_pos={end_pos - overlap_amount}, chunk_size={len(chunk_text)}, adjusted new_pos={new_pos}")
            
            # 确保不超过文本长度
            if new_pos >= len(clean_section_text):
                break
                
            current_pos = new_pos
            chunk_index += 1
        
        logger.debug(f"Created {len(chunks)} chunks from section of {len(clean_section_text)} chars (heading_path: {heading_path})")
        if len(chunks) > 50:
            logger.warning(f"WARNING: Created {len(chunks)} chunks from section of only {len(clean_section_text)} chars! This seems excessive.")
            # 记录一些chunk的大小信息用于诊断
            chunk_sizes = [len(c.text) for c in chunks]
            logger.warning(f"Chunk sizes: min={min(chunk_sizes)}, max={max(chunk_sizes)}, avg={sum(chunk_sizes)/len(chunk_sizes):.1f}")
            # 记录前5个chunk的详细信息
            for i, c in enumerate(chunks[:5]):
                logger.warning(f"  Chunk {i}: size={len(c.text)}, start={c.location.start_char}, end={c.location.end_char}")
            # 检查是否有重复的chunk
            chunk_texts = [c.text[:50] for c in chunks[:10]]  # 前10个chunk的前50字符
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

