#!/usr/bin/env python3
"""Detailed test for pymupdf4llm - focusing on implementation details."""
import sys
from pathlib import Path
import re
import json
from typing import List, Dict, Any

try:
    import pymupdf4llm
    import fitz  # PyMuPDF
    print("[OK] pymupdf4llm and PyMuPDF are installed")
except ImportError as e:
    print(f"[ERROR] Missing dependencies: {e}")
    sys.exit(1)


def test_page_chunks_structure(pdf_path: Path):
    """Test the actual structure of page_chunks return value."""
    print("\n" + "="*60)
    print("[Detailed Test] Page Chunks Structure")
    print("="*60)
    
    page_chunks = pymupdf4llm.to_markdown(str(pdf_path), page_chunks=True)
    
    print(f"Total pages: {len(page_chunks)}")
    print(f"\nFirst chunk structure:")
    if len(page_chunks) > 0:
        first_chunk = page_chunks[0]
        print(f"  Type: {type(first_chunk)}")
        print(f"  Keys: {list(first_chunk.keys())}")
        
        # Check each key
        for key in first_chunk.keys():
            value = first_chunk[key]
            value_type = type(value).__name__
            if isinstance(value, (str, int, float, bool, type(None))):
                print(f"  {key}: {value_type} = {str(value)[:100]}")
            elif isinstance(value, list):
                print(f"  {key}: list with {len(value)} items")
                if len(value) > 0:
                    print(f"    First item type: {type(value[0]).__name__}")
                    if isinstance(value[0], dict):
                        print(f"    First item keys: {list(value[0].keys())[:5]}")
            elif isinstance(value, dict):
                print(f"  {key}: dict with {len(value)} keys")
                print(f"    Keys: {list(value.keys())[:5]}")
        
        # Check text field specifically
        if 'text' in first_chunk:
            text = first_chunk['text']
            print(f"\n  'text' field:")
            print(f"    Type: {type(text)}")
            print(f"    Length: {len(text) if isinstance(text, str) else 'N/A'}")
            print(f"    Preview: {str(text)[:200]}...")
        
        # Check if there's page number info
        print(f"\n  Checking for page number:")
        if 'metadata' in first_chunk:
            metadata = first_chunk['metadata']
            print(f"    metadata type: {type(metadata)}")
            if isinstance(metadata, dict):
                print(f"    metadata keys: {list(metadata.keys())}")
                if 'page' in metadata:
                    print(f"    metadata['page']: {metadata['page']}")
        
        # Check tables field
        if 'tables' in first_chunk:
            tables = first_chunk['tables']
            print(f"\n  'tables' field:")
            print(f"    Type: {type(tables)}")
            if isinstance(tables, list):
                print(f"    Number of tables: {len(tables)}")
                if len(tables) > 0:
                    print(f"    First table type: {type(tables[0])}")
                    if isinstance(tables[0], dict):
                        print(f"    First table keys: {list(tables[0].keys())}")
            elif isinstance(tables, dict):
                print(f"    Tables dict keys: {list(tables.keys())}")
        
        # Check images field
        if 'images' in first_chunk:
            images = first_chunk['images']
            print(f"\n  'images' field:")
            print(f"    Type: {type(images)}")
            if isinstance(images, list):
                print(f"    Number of images: {len(images)}")
                if len(images) > 0:
                    print(f"    First image type: {type(images[0])}")
                    if isinstance(images[0], dict):
                        print(f"    First image keys: {list(images[0].keys())}")
                        print(f"    First image: {images[0]}")
        
        # Check graphics field
        if 'graphics' in first_chunk:
            graphics = first_chunk['graphics']
            print(f"\n  'graphics' field:")
            print(f"    Type: {type(graphics)}")
            if isinstance(graphics, list):
                print(f"    Number of graphics: {len(graphics)}")
    
    # Check all pages for page number info
    print(f"\n  Checking all pages for page number:")
    for i, chunk in enumerate(page_chunks):
        page_num_found = False
        if 'metadata' in chunk and isinstance(chunk['metadata'], dict):
            if 'page' in chunk['metadata']:
                print(f"    Page {i}: metadata['page'] = {chunk['metadata']['page']}")
                page_num_found = True
        if not page_num_found:
            print(f"    Page {i}: No page number found in metadata")


def test_image_extraction_detailed(pdf_path: Path):
    """Test image extraction in detail."""
    print("\n" + "="*60)
    print("[Detailed Test] Image Extraction")
    print("="*60)
    
    # Test 1: Without write_images
    print("\n1. Testing without write_images:")
    md_text_no_img = pymupdf4llm.to_markdown(str(pdf_path), write_images=False)
    img_refs_no_img = re.findall(r'!\[.*?\]\((.*?)\)', md_text_no_img)
    print(f"   Image references: {len(img_refs_no_img)}")
    
    # Test 2: With write_images
    print("\n2. Testing with write_images=True:")
    md_text_with_img = pymupdf4llm.to_markdown(str(pdf_path), write_images=True)
    img_refs_with_img = re.findall(r'!\[.*?\]\((.*?)\)', md_text_with_img)
    print(f"   Image references in markdown: {len(img_refs_with_img)}")
    if img_refs_with_img:
        print(f"   References: {img_refs_with_img}")
    
    # Check PDF directory for images
    pdf_dir = pdf_path.parent
    pdf_name = pdf_path.stem
    print(f"\n3. Checking for image files in PDF directory:")
    print(f"   PDF directory: {pdf_dir}")
    print(f"   PDF name: {pdf_name}")
    
    # Look for images with various patterns
    patterns = [
        f"{pdf_name}*.png",
        f"{pdf_name}*.jpg",
        f"{pdf_name}*.jpeg",
        f"{pdf_path.name}*.png",
        f"{pdf_path.name}*.jpg",
        "*.png",  # All PNGs in directory
    ]
    
    for pattern in patterns:
        images = list(pdf_dir.glob(pattern))
        if images:
            print(f"   Found with pattern '{pattern}': {len(images)} files")
            for img in images[:5]:
                print(f"     - {img.name} ({img.stat().st_size} bytes)")
    
    # Check page_chunks for images field
    print(f"\n4. Checking page_chunks for images:")
    page_chunks = pymupdf4llm.to_markdown(str(pdf_path), page_chunks=True, write_images=True)
    total_images = 0
    for i, chunk in enumerate(page_chunks):
        if 'images' in chunk:
            images = chunk['images']
            if isinstance(images, list):
                if len(images) > 0:
                    print(f"   Page {i}: {len(images)} images")
                    for img in images:
                        print(f"     {img}")
                    total_images += len(images)
            elif images:
                print(f"   Page {i}: images = {images}")
    
    print(f"\n   Total images in page_chunks: {total_images}")


def test_table_extraction(pdf_path: Path):
    """Test table extraction from page_chunks."""
    print("\n" + "="*60)
    print("[Detailed Test] Table Extraction")
    print("="*60)
    
    page_chunks = pymupdf4llm.to_markdown(str(pdf_path), page_chunks=True)
    
    total_tables = 0
    for i, chunk in enumerate(page_chunks):
        if 'tables' in chunk:
            tables = chunk['tables']
            if isinstance(tables, list) and len(tables) > 0:
                print(f"\nPage {i}: {len(tables)} tables")
                for j, table in enumerate(tables):
                    print(f"  Table {j}:")
                    print(f"    Type: {type(table)}")
                    if isinstance(table, dict):
                        print(f"    Keys: {list(table.keys())}")
                        # Try to find table content
                        for key in ['markdown', 'text', 'content', 'html', 'cells', 'rows']:
                            if key in table:
                                value = table[key]
                                if isinstance(value, str):
                                    print(f"    {key}: {value[:200]}...")
                                else:
                                    print(f"    {key}: {type(value)} = {value}")
                    elif isinstance(table, str):
                        print(f"    Content: {table[:200]}...")
                total_tables += len(tables)
    
    # Also check markdown text for tables
    print(f"\nChecking markdown text for tables:")
    md_text = pymupdf4llm.to_markdown(str(pdf_path))
    table_pattern = r'(\|[^\n]+\|\n\|[:\s\-]+\|\n(?:\|[^\n]+\|\n?)+)'
    table_matches = list(re.finditer(table_pattern, md_text, re.MULTILINE))
    print(f"  Tables in markdown: {len(table_matches)}")
    
    print(f"\nTotal tables found: {total_tables} (from page_chunks)")


def test_chunking_strategy(pdf_path: Path):
    """Test different chunking strategies."""
    print("\n" + "="*60)
    print("[Detailed Test] Chunking Strategy")
    print("="*60)
    
    # Strategy 1: Full markdown
    print("\n1. Full markdown (single string):")
    full_md = pymupdf4llm.to_markdown(str(pdf_path))
    print(f"   Length: {len(full_md)} characters")
    print(f"   Has page info: {'<page' in full_md or 'page' in full_md.lower()}")
    
    # Strategy 2: Page chunks
    print("\n2. Page chunks:")
    page_chunks = pymupdf4llm.to_markdown(str(pdf_path), page_chunks=True)
    print(f"   Number of pages: {len(page_chunks)}")
    
    # Combine pages with page markers
    print("\n3. Combining pages with markers:")
    combined_parts = []
    current_pos = 0
    
    for i, chunk in enumerate(page_chunks):
        page_num = i + 1  # 0-based to 1-based
        text = chunk.get('text', '')
        
        # Add page marker
        page_start = f'<page page="{page_num}" start_char="{current_pos}">\n\n'
        combined_parts.append(page_start)
        current_pos += len(page_start)
        
        # Add page content
        combined_parts.append(text)
        current_pos += len(text)
        
        # Close page marker
        page_end = '\n\n</page>\n\n'
        combined_parts.append(page_end)
        current_pos += len(page_end)
    
    combined_md = ''.join(combined_parts)
    print(f"   Combined length: {len(combined_md)} characters")
    print(f"   Number of page markers: {combined_md.count('<page')}")
    
    # Test chunking on combined text
    print("\n4. Testing chunking on combined text:")
    # Simulate chunking (split by double newlines)
    chunks = combined_md.split('\n\n\n')
    print(f"   Potential chunks (by \\n\\n\\n): {len(chunks)}")
    print(f"   Average chunk size: {sum(len(c) for c in chunks) / len(chunks) if chunks else 0:.0f} chars")


def test_file_location_tracking(pdf_path: Path):
    """Test how to track file locations for citation."""
    print("\n" + "="*60)
    print("[Detailed Test] File Location Tracking")
    print("="*60)
    
    page_chunks = pymupdf4llm.to_markdown(str(pdf_path), page_chunks=True)
    
    print(f"PDF path: {pdf_path}")
    print(f"PDF absolute path: {pdf_path.resolve()}")
    print(f"PDF name: {pdf_path.name}")
    print(f"PDF stem: {pdf_path.stem}")
    
    # Build location map
    print("\nBuilding location map:")
    location_map = []
    current_char_pos = 0
    
    for i, chunk in enumerate(page_chunks):
        page_num = i + 1
        text = chunk.get('text', '')
        text_length = len(text)
        
        location_map.append({
            'page': page_num,
            'start_char': current_char_pos,
            'end_char': current_char_pos + text_length,
            'length': text_length
        })
        
        current_char_pos += text_length
    
    print(f"  Total pages: {len(location_map)}")
    print(f"  Total characters: {current_char_pos}")
    print(f"\n  Sample locations:")
    for loc in location_map[:3]:
        print(f"    Page {loc['page']}: chars {loc['start_char']}-{loc['end_char']} ({loc['length']} chars)")


def main():
    if len(sys.argv) < 2:
        print("Usage: python test_pymupdf4llm_detailed.py <pdf_path>")
        sys.exit(1)
    
    pdf_path = Path(sys.argv[1])
    
    if not pdf_path.exists():
        print(f"✗ PDF file not found: {pdf_path}")
        sys.exit(1)
    
    print("="*60)
    print("Detailed pymupdf4llm Test - Implementation Focus")
    print("="*60)
    print(f"PDF file: {pdf_path}")
    
    test_page_chunks_structure(pdf_path)
    test_image_extraction_detailed(pdf_path)
    test_table_extraction(pdf_path)
    test_chunking_strategy(pdf_path)
    test_file_location_tracking(pdf_path)
    
    print("\n" + "="*60)
    print("Test Complete")
    print("="*60)


if __name__ == "__main__":
    main()

