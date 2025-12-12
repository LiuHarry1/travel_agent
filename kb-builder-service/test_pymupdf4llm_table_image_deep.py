#!/usr/bin/env python3
"""Deep analysis of table and image extraction."""
import sys
from pathlib import Path
import re
import json

try:
    import pymupdf4llm
    import fitz  # PyMuPDF
    print("[OK] pymupdf4llm and PyMuPDF are installed")
except ImportError as e:
    print(f"[ERROR] Missing dependencies: {e}")
    sys.exit(1)


def analyze_table_content_in_markdown(pdf_path: Path):
    """Analyze if table content is in markdown text."""
    print("\n" + "="*60)
    print("[Deep Analysis] Table Content in Markdown")
    print("="*60)
    
    page_chunks = pymupdf4llm.to_markdown(str(pdf_path), page_chunks=True)
    
    # Find pages with tables
    pages_with_tables = []
    for chunk in page_chunks:
        if chunk.get('tables') and len(chunk['tables']) > 0:
            pages_with_tables.append(chunk)
    
    print(f"\nFound {len(pages_with_tables)} pages with tables")
    
    # Analyze first page with tables
    if pages_with_tables:
        first_chunk = pages_with_tables[0]
        page_num = first_chunk['metadata']['page']
        page_text = first_chunk.get('text', '')
        tables = first_chunk.get('tables', [])
        
        print(f"\nAnalyzing page {page_num}:")
        print(f"  Text length: {len(page_text)} characters")
        print(f"  Number of tables: {len(tables)}")
        
        # Check for table-like patterns in text
        # Pattern 1: Standard markdown table
        md_table_pattern = r'(\|[^\n]+\|\n\|[:\s\-]+\|\n(?:\|[^\n]+\|\n?)+)'
        md_tables = list(re.finditer(md_table_pattern, page_text, re.MULTILINE))
        print(f"  Standard markdown tables: {len(md_tables)}")
        
        # Pattern 2: Lines with multiple spaces (potential table)
        lines = page_text.split('\n')
        table_like_lines = []
        for i, line in enumerate(lines):
            # Check if line has multiple spaces (potential table row)
            if line.count('  ') >= 3 and len(line.strip()) > 10:
                table_like_lines.append((i, line[:100]))
        
        print(f"  Table-like lines (multiple spaces): {len(table_like_lines)}")
        if table_like_lines:
            print(f"  Sample lines:")
            for line_num, line_text in table_like_lines[:5]:
                print(f"    Line {line_num}: {line_text}...")
        
        # Pattern 3: Check for table structure in text
        # Look for repeated patterns (rows)
        if tables:
            first_table = tables[0]
            rows = first_table.get('rows', 0)
            cols = first_table.get('columns', 0)
            bbox = first_table.get('bbox', None)
            
            print(f"\n  First table info:")
            print(f"    Rows: {rows}, Columns: {cols}")
            print(f"    Bbox: {bbox}")
            
            # Try to find content near bbox position
            if bbox:
                print(f"    Looking for content in bbox area...")
        
        # Show sample text around potential table area
        print(f"\n  Sample text from page (first 1000 chars):")
        # Use repr to avoid encoding issues
        sample_text = repr(page_text[:200])
        print(f"  {sample_text}...")
        
        # Check if table content is in a different format
        # Look for structured data patterns
        if '|' in page_text:
            pipe_count = page_text.count('|')
            print(f"\n  Pipe characters (|) in text: {pipe_count}")
            if pipe_count > 0:
                # Find lines with pipes
                pipe_lines = [line for line in lines if '|' in line]
                print(f"  Lines with pipes: {len(pipe_lines)}")
                if pipe_lines:
                    print(f"  Sample pipe lines:")
                    for line in pipe_lines[:5]:
                        print(f"    {line[:100]}...")


def analyze_image_references(pdf_path: Path):
    """Analyze image references in detail."""
    print("\n" + "="*60)
    print("[Deep Analysis] Image References")
    print("="*60)
    
    # Test with write_images=True
    md_with_img = pymupdf4llm.to_markdown(str(pdf_path), write_images=True)
    
    # Find all image references
    img_pattern = r'!\[([^\]]*)\]\(([^\)]+)\)'
    img_matches = list(re.finditer(img_pattern, md_with_img))
    
    print(f"\nFound {len(img_matches)} image references in markdown")
    
    if img_matches:
        print(f"\nFirst 5 image references:")
        for i, match in enumerate(img_matches[:5]):
            alt_text = match.group(1)
            img_path = match.group(2)
            print(f"  {i+1}. Alt: '{alt_text}', Path: '{img_path}'")
            
            # Check if path looks like a file reference
            if img_path.endswith(('.png', '.jpg', '.jpeg')):
                print(f"     Looks like image file: {img_path}")
    
    # Check page_chunks for images
    print(f"\nChecking page_chunks for images field:")
    page_chunks = pymupdf4llm.to_markdown(str(pdf_path), page_chunks=True, write_images=True)
    
    total_images_in_chunks = 0
    for chunk in page_chunks:
        images = chunk.get('images', [])
        if images:
            page_num = chunk['metadata']['page']
            print(f"  Page {page_num}: {len(images)} images in 'images' field")
            total_images_in_chunks += len(images)
    
    print(f"\n  Total images in page_chunks 'images' field: {total_images_in_chunks}")
    
    # Compare with PyMuPDF
    print(f"\nComparing with PyMuPDF direct extraction:")
    doc = fitz.open(str(pdf_path))
    total_pages = len(doc)
    
    pymupdf_image_count = 0
    for page_num in range(total_pages):
        page = doc[page_num]
        image_list = page.get_images()
        if image_list:
            pymupdf_image_count += len(image_list)
            print(f"  Page {page_num + 1}: {len(image_list)} images")
    
    doc.close()
    print(f"\n  Total PyMuPDF images: {pymupdf_image_count}")
    
    # Check if images are embedded in markdown as base64 or other format
    print(f"\nChecking for embedded images in markdown:")
    # Look for base64 data URLs
    base64_pattern = r'data:image/[^;]+;base64,[A-Za-z0-9+/=]+'
    base64_matches = re.findall(base64_pattern, md_with_img)
    print(f"  Base64 embedded images: {len(base64_matches)}")
    
    # Look for other image formats
    if '<img' in md_with_img.lower():
        print(f"  Found HTML <img> tags in markdown")
        img_tag_pattern = r'<img[^>]+>'
        img_tags = re.findall(img_tag_pattern, md_with_img, re.IGNORECASE)
        print(f"  Number of <img> tags: {len(img_tags)}")
        if img_tags:
            print(f"  Sample: {img_tags[0][:200]}...")


def analyze_table_structure_deep(pdf_path: Path):
    """Deep analysis of table structure."""
    print("\n" + "="*60)
    print("[Deep Analysis] Table Structure Deep Dive")
    print("="*60)
    
    page_chunks = pymupdf4llm.to_markdown(str(pdf_path), page_chunks=True)
    
    # Find first page with tables
    first_table_chunk = None
    for chunk in page_chunks:
        if chunk.get('tables') and len(chunk['tables']) > 0:
            first_table_chunk = chunk
            break
    
    if not first_table_chunk:
        print("No tables found")
        return
    
    page_num = first_table_chunk['metadata']['page']
    page_text = first_table_chunk.get('text', '')
    first_table = first_table_chunk['tables'][0]
    
    print(f"\nAnalyzing first table on page {page_num}:")
    print(f"  Table structure: {first_table}")
    
    # Check if table content is in the text
    bbox = first_table.get('bbox', None)
    rows = first_table.get('rows', 0)
    cols = first_table.get('columns', 0)
    
    print(f"\n  Table metadata:")
    print(f"    Rows: {rows}")
    print(f"    Columns: {cols}")
    print(f"    Bbox: {bbox}")
    
    # Try to extract table content from text
    # Look for structured patterns
    lines = page_text.split('\n')
    
    print(f"\n  Analyzing text for table content:")
    print(f"    Total lines: {len(lines)}")
    
    # Look for lines that might be table rows
    # Pattern: lines with consistent spacing or separators
    potential_table_lines = []
    for i, line in enumerate(lines):
        stripped = line.strip()
        if not stripped:
            continue
        
        # Check for multiple spaces (potential table)
        if stripped.count('  ') >= cols - 1:
            potential_table_lines.append((i, line))
        # Check for tabs
        elif '\t' in stripped:
            potential_table_lines.append((i, line))
        # Check for consistent separators
        elif '|' in stripped:
            potential_table_lines.append((i, line))
    
    print(f"    Potential table lines: {len(potential_table_lines)}")
    
    if potential_table_lines and len(potential_table_lines) >= rows:
        print(f"    Found {len(potential_table_lines)} lines that might be table rows")
        print(f"    Sample lines:")
        for line_num, line_text in potential_table_lines[:min(rows, 10)]:
            print(f"      Line {line_num}: {line_text[:100]}...")
    
    # Check if table is formatted differently
    # Maybe it's in a code block or special format
    code_block_pattern = r'```[\s\S]*?```'
    code_blocks = re.findall(code_block_pattern, page_text)
    if code_blocks:
        print(f"\n    Found {len(code_blocks)} code blocks")
        for i, block in enumerate(code_blocks[:3]):
            if '|' in block or block.count('  ') > 10:
                print(f"      Code block {i+1} might contain table:")
                print(f"      {block[:300]}...")


def main():
    # Convert file:// URL to Windows path
    if len(sys.argv) < 2:
        pdf_path_str = "file:///C:/Users/Harry/Documents/job/Advantest/digital_test_fundemantal/%E5%AE%9E%E9%AA%8C/SN74HC163DataSheet.pdf"
    else:
        pdf_path_str = sys.argv[1]
    
    # Handle file:// URL
    if pdf_path_str.startswith("file:///"):
        pdf_path_str = pdf_path_str[8:]
        import urllib.parse
        pdf_path_str = urllib.parse.unquote(pdf_path_str)
    
    pdf_path = Path(pdf_path_str)
    
    if not pdf_path.exists():
        print(f"[ERROR] PDF file not found: {pdf_path}")
        sys.exit(1)
    
    print("="*60)
    print("pymupdf4llm Deep Analysis - Tables and Images")
    print("="*60)
    print(f"PDF file: {pdf_path}")
    
    analyze_table_content_in_markdown(pdf_path)
    analyze_image_references(pdf_path)
    analyze_table_structure_deep(pdf_path)
    
    print("\n" + "="*60)
    print("Deep Analysis Complete")
    print("="*60)


if __name__ == "__main__":
    main()

