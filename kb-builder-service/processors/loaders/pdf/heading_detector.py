"""PDF heading detection based on font analysis."""
from typing import List, Dict, Optional
from collections import defaultdict
from utils.logger import get_logger

logger = get_logger(__name__)


class HeadingDetector:
    """Detects headings in PDF documents based on font analysis."""
    
    def __init__(self, sample_pages: Optional[int] = 5):
        """
        Args:
            sample_pages: Number of pages to sample for font distribution analysis (None = analyze all pages)
        """
        self.sample_pages = sample_pages
    
    def detect(self, pdf) -> List[Dict]:
        """
        Detect headings in PDF based on font size, boldness, and position.
        
        Args:
            pdf: pdfplumber PDF object
        
        Returns:
            List of heading dictionaries with format:
            [{"level": 1, "text": "标题", "page": 1, "start_char": 100, "font_size": 16.0}]
        """
        headings = []
        all_chars = []
        char_offset = 0
        
        # Determine pages to analyze for font distribution
        total_pages = len(pdf.pages)
        if self.sample_pages and total_pages > self.sample_pages:
            # Sample first N pages for font distribution
            sample_page_range = range(1, min(self.sample_pages + 1, total_pages + 1))
            logger.debug(f"Sampling first {self.sample_pages} pages for font distribution analysis")
        else:
            # Analyze all pages
            sample_page_range = range(1, total_pages + 1)
        
        # Collect character information from sample pages for font analysis
        sample_chars = []
        for page_num in sample_page_range:
            page = pdf.pages[page_num - 1]
            chars = page.chars
            if not chars:
                continue
            
            for char in chars:
                sample_chars.append({
                    'size': char.get('size', 0),
                    'fontname': char.get('fontname', ''),
                })
        
        if not sample_chars:
            return []
        
        # Analyze font size distribution from sample
        font_sizes = [c['size'] for c in sample_chars if c['size'] > 0]
        if not font_sizes:
            return []
        
        # Calculate font size statistics
        font_sizes_sorted = sorted(set(font_sizes), reverse=True)
        median_size = sorted(font_sizes)[len(font_sizes) // 2]
        avg_size = sum(font_sizes) / len(font_sizes)
        
        # Identify heading fonts: significantly larger than body text
        heading_threshold = max(avg_size * 1.2, median_size * 1.15)
        
        logger.debug(f"Font analysis: avg={avg_size:.2f}, median={median_size:.2f}, threshold={heading_threshold:.2f}")
        
        # Now collect all characters from all pages for heading detection
        for page_num, page in enumerate(pdf.pages, 1):
            chars = page.chars
            if not chars:
                continue
            
            for char in chars:
                all_chars.append({
                    'text': char.get('text', ''),
                    'size': char.get('size', 0),
                    'fontname': char.get('fontname', ''),
                    'x0': char.get('x0', 0),
                    'y0': char.get('y0', 0),
                    'x1': char.get('x1', 0),
                    'y1': char.get('y1', 0),
                    'page': page_num,
                    'offset': char_offset
                })
                char_offset += len(char.get('text', ''))
        
        if not all_chars:
            return []
        
        # Detect bold fonts
        def is_bold(fontname: str) -> bool:
            fontname_lower = fontname.lower()
            return any(keyword in fontname_lower for keyword in ['bold', 'black', 'heavy', 'demibold'])
        
        # Map font sizes to 6 levels
        heading_font_sizes = [s for s in font_sizes_sorted if s >= heading_threshold]
        
        if not heading_font_sizes:
            # If no significantly larger fonts, try bold fonts
            heading_font_sizes = [s for s in font_sizes_sorted if any(is_bold(c['fontname']) for c in all_chars if c['size'] == s)]
        
        if not heading_font_sizes:
            return []
        
        # Map heading font sizes to 6 levels
        if len(heading_font_sizes) >= 6:
            level_font_sizes = {}
            for i, size in enumerate(heading_font_sizes[:6]):
                level_font_sizes[i + 1] = size
        else:
            # Use quantiles if fewer font sizes
            level_font_sizes = {}
            min_size = min(heading_font_sizes)
            max_size = max(heading_font_sizes)
            size_range = max_size - min_size
            for level in range(1, 7):
                ratio = (7 - level) / 6
                level_font_sizes[level] = max_size - size_range * (1 - ratio)
        
        # Identify heading lines: characters on the same line
        def get_line_key(char):
            """Determine line based on y coordinate."""
            return round(char['y0'] / 2) * 2
        
        # Group characters by line (using defaultdict for efficiency)
        lines = defaultdict(list)
        for char in all_chars:
            line_key = get_line_key(char)
            lines[line_key].append(char)
        
        # Sort each line by x coordinate
        for line_key in lines:
            lines[line_key].sort(key=lambda c: c['x0'])
        
        # Identify heading lines
        for line_key, line_chars in sorted(lines.items(), key=lambda x: -x[0]):  # Top to bottom
            if not line_chars:
                continue
            
            first_char = line_chars[0]
            font_size = first_char['size']
            fontname = first_char['fontname']
            page_num = first_char['page']
            
            # Check if this line is a heading
            is_heading = False
            heading_level = None
            
            # Find closest heading level
            for level in range(1, 7):
                if level in level_font_sizes:
                    target_size = level_font_sizes[level]
                    if abs(font_size - target_size) / max(target_size, 1) < 0.15:
                        is_heading = True
                        heading_level = level
                        break
            
            # If font size doesn't match but font is bold, might still be heading
            if not is_heading and is_bold(fontname) and font_size >= heading_threshold * 0.9:
                if font_size >= max(heading_font_sizes) * 0.9:
                    heading_level = 1
                elif font_size >= max(heading_font_sizes) * 0.7:
                    heading_level = 2
                elif font_size >= max(heading_font_sizes) * 0.5:
                    heading_level = 3
                else:
                    heading_level = 4
                is_heading = True
            
            if is_heading and heading_level:
                # Merge characters on same line to form heading text
                heading_text = ''.join(c['text'] for c in line_chars).strip()
                
                # Filter out too short text (might be page numbers, headers, etc.)
                if len(heading_text) < 2:
                    continue
                
                # Filter out pure numbers or special characters (might be page numbers)
                if heading_text.replace('.', '').replace(' ', '').isdigit():
                    continue
                
                # Calculate heading position in document
                start_char = line_chars[0]['offset']
                
                headings.append({
                    "level": heading_level,
                    "text": heading_text,
                    "page": page_num,
                    "start_char": start_char,
                    "font_size": font_size
                })
        
        # Sort by position
        headings.sort(key=lambda h: (h['page'], h['start_char']))
        
        logger.info(f"Detected {len(headings)} headings in PDF")
        if headings:
            logger.debug(f"Sample headings: {headings[:5]}")
        
        return headings
