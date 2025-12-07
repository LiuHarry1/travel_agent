"""Location information extractor."""
import re
from typing import Optional
from models.chunk import ChunkLocation


class LocationExtractor:
    """Extract location information from chunk text."""
    
    @staticmethod
    def extract_for_pdf(chunk_text: str, chunk_start: int, chunk_end: int) -> ChunkLocation:
        """Extract location information from PDF chunk."""
        location = ChunkLocation(
            start_char=chunk_start,
            end_char=chunk_end
        )
        
        # 提取页面号
        page_match = re.search(r'<page\s+page="(\d+)"', chunk_text, re.IGNORECASE)
        if page_match:
            location.page_number = int(page_match.group(1))
        
        # 提取图片信息
        img_match = re.search(r'<img[^>]+src="([^"]+)"', chunk_text, re.IGNORECASE)
        if img_match:
            location.image_url = img_match.group(1)
            # 提取图片索引
            img_idx_match = re.search(r'image_index="(\d+)"', chunk_text, re.IGNORECASE)
            if img_idx_match:
                location.image_index = int(img_idx_match.group(1))
        
        # 提取表格信息
        table_match = re.search(r'<table[^>]+index="(\d+)"', chunk_text, re.IGNORECASE)
        if table_match:
            location.table_index = int(table_match.group(1))
        
        return location
    
    @staticmethod
    def extract_for_docx(chunk_text: str, chunk_start: int, chunk_end: int) -> ChunkLocation:
        """Extract location information from DOCX chunk."""
        location = ChunkLocation(
            start_char=chunk_start,
            end_char=chunk_end
        )
        
        # 提取段落索引
        para_match = re.search(r'<paragraph\s+index="(\d+)"', chunk_text, re.IGNORECASE)
        if para_match:
            location.paragraph_index = int(para_match.group(1))
        
        # 提取图片信息
        img_match = re.search(r'<img[^>]+src="([^"]+)"', chunk_text, re.IGNORECASE)
        if img_match:
            location.image_url = img_match.group(1)
        
        return location
    
    @staticmethod
    def extract_for_html(chunk_text: str, chunk_start: int, chunk_end: int) -> ChunkLocation:
        """Extract location information from HTML chunk."""
        location = ChunkLocation(
            start_char=chunk_start,
            end_char=chunk_end
        )
        
        # 提取标题路径（从Markdown格式的标题）
        headings = []
        heading_pattern = r'^(#{1,6})\s+(.+)$'
        for match in re.finditer(heading_pattern, chunk_text, re.MULTILINE):
            level = len(match.group(1))
            text = match.group(2).strip()
            headings.append(f"H{level}: {text}")
        
        if headings:
            location.heading_path = headings
        
        # 提取图片信息
        img_match = re.search(r'<img[^>]+src="([^"]+)"', chunk_text, re.IGNORECASE)
        if img_match:
            location.image_url = img_match.group(1)
        
        return location
    
    @staticmethod
    def extract_for_markdown(chunk_text: str, chunk_start: int, chunk_end: int) -> ChunkLocation:
        """Extract location information from Markdown chunk."""
        location = ChunkLocation(
            start_char=chunk_start,
            end_char=chunk_end
        )
        
        # 提取标题路径
        headings = []
        heading_pattern = r'^(#{1,6})\s+(.+)$'
        for match in re.finditer(heading_pattern, chunk_text, re.MULTILINE):
            level = len(match.group(1))
            text = match.group(2).strip()
            headings.append(text)
        
        if headings:
            location.heading_path = headings
        
        # 提取代码块索引
        code_blocks = list(re.finditer(r'```(\w+)?\n(.*?)```', chunk_text, re.DOTALL))
        if code_blocks:
            location.code_block_index = 0  # 第一个代码块
        
        # 提取图片信息
        img_match = re.search(r'!\[([^\]]*)\]\(([^)]+)\)', chunk_text)
        if img_match:
            location.image_url = img_match.group(2)
        
        return location

