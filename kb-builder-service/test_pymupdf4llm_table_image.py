#!/usr/bin/env python3
"""Detailed test for pymupdf4llm table and image extraction."""
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


def test_table_extraction_detailed(pdf_path: Path):
    """Test table extraction in detail."""
    print("\n" + "="*60)
    print("[Test] Table Extraction - Detailed Analysis")
    print("="*60)
    
    # Test 1: Full markdown
    print("\n1. Testing full markdown conversion:")
    full_md = pymupdf4llm.to_markdown(str(pdf_path))
    
    # Check for tables in markdown
    table_pattern = r'(\|[^\n]+\|\n\|[:\s\-]+\|\n(?:\|[^\n]+\|\n?)+)'
    table_matches = list(re.finditer(table_pattern, full_md, re.MULTILINE))
    print(f"   Tables in markdown: {len(table_matches)}")
    
    if table_matches:
        print(f"\n   Sample table (first 500 chars):")
        print(f"   {table_matches[0].group(1)[:500]}...")
    
    # Test 2: Page chunks with tables field
    print("\n2. Testing page_chunks with tables field:")
    page_chunks = pymupdf4llm.to_markdown(str(pdf_path), page_chunks=True)
    
    total_tables = 0
    tables_by_page = []
    
    for i, chunk in enumerate(page_chunks):
        page_num = chunk['metadata']['page']
        tables = chunk.get('tables', [])
        
        if tables:
            print(f"\n   Page {page_num} (index {i}): {len(tables)} tables")
            total_tables += len(tables)
            
            for j, table in enumerate(tables):
                print(f"     Table {j}:")
                print(f"       Type: {type(table)}")
                
                if isinstance(table, dict):
                    print(f"       Keys: {list(table.keys())}")
                    # Print all key-value pairs
                    for key, value in table.items():
                        if isinstance(value, (str, int, float, bool, type(None))):
                            print(f"       {key}: {value}")
                        elif isinstance(value, list):
                            print(f"       {key}: list with {len(value)} items")
                            if len(value) > 0:
                                print(f"         First item type: {type(value[0]).__name__}")
                                if isinstance(value[0], dict):
                                    print(f"         First item keys: {list(value[0].keys())[:5]}")
                        elif isinstance(value, dict):
                            print(f"       {key}: dict with {len(value)} keys")
                            print(f"         Keys: {list(value.keys())[:5]}")
                elif isinstance(table, str):
                    print(f"       Content (first 200 chars): {table[:200]}...")
                else:
                    print(f"       Content: {str(table)[:200]}...")
                
                tables_by_page.append({
                    'page': page_num,
                    'index': j,
                    'table': table
                })
    
    print(f"\n   Total tables from page_chunks: {total_tables}")
    
    # Test 3: Compare tables in markdown vs page_chunks
    print("\n3. Comparing tables in markdown vs page_chunks:")
    print(f"   Markdown tables: {len(table_matches)}")
    print(f"   page_chunks tables: {total_tables}")
    
    # Save detailed table info
    table_info = {
        'markdown_tables': len(table_matches),
        'page_chunks_tables': total_tables,
        'tables_by_page': []
    }
    
    for item in tables_by_page[:5]:  # First 5 tables
        table_data = item['table']
        if isinstance(table_data, dict):
            table_info['tables_by_page'].append({
                'page': item['page'],
                'index': item['index'],
                'keys': list(table_data.keys()) if isinstance(table_data, dict) else None,
                'type': type(table_data).__name__
            })
    
    return table_info


def test_image_extraction_detailed(pdf_path: Path):
    """Test image extraction in detail."""
    print("\n" + "="*60)
    print("[Test] Image Extraction - Detailed Analysis")
    print("="*60)
    
    # Test 1: Without write_images
    print("\n1. Testing without write_images:")
    md_no_img = pymupdf4llm.to_markdown(str(pdf_path), write_images=False)
    img_refs_no = re.findall(r'!\[.*?\]\((.*?)\)', md_no_img)
    print(f"   Image references in markdown: {len(img_refs_no)}")
    
    # Test 2: With write_images
    print("\n2. Testing with write_images=True:")
    md_with_img = pymupdf4llm.to_markdown(str(pdf_path), write_images=True)
    img_refs_with = re.findall(r'!\[.*?\]\((.*?)\)', md_with_img)
    print(f"   Image references in markdown: {len(img_refs_with)}")
    if img_refs_with:
        print(f"   References: {img_refs_with[:5]}")
    
    # Test 3: Check page_chunks images field
    print("\n3. Testing page_chunks images field:")
    page_chunks = pymupdf4llm.to_markdown(str(pdf_path), page_chunks=True, write_images=True)
    
    total_images = 0
    images_by_page = []
    
    for i, chunk in enumerate(page_chunks):
        page_num = chunk['metadata']['page']
        images = chunk.get('images', [])
        
        if images:
            print(f"\n   Page {page_num} (index {i}): {len(images)} images")
            total_images += len(images)
            
            for j, img in enumerate(images):
                print(f"     Image {j}:")
                print(f"       Type: {type(img)}")
                
                if isinstance(img, dict):
                    print(f"       Keys: {list(img.keys())}")
                    # Print key-value pairs
                    for key, value in img.items():
                        if isinstance(value, (str, int, float, bool, type(None))):
                            print(f"       {key}: {value}")
                        elif isinstance(value, (list, dict)):
                            print(f"       {key}: {type(value).__name__} with {len(value)} items")
                
                images_by_page.append({
                    'page': page_num,
                    'index': j,
                    'image': img
                })
    
    print(f"\n   Total images from page_chunks: {total_images}")
    
    # Test 4: Extract images using PyMuPDF
    print("\n4. Testing direct PyMuPDF image extraction:")
    doc = fitz.open(str(pdf_path))
    total_pages = len(doc)
    
    pymupdf_images = []
    for page_num in range(total_pages):
        page = doc[page_num]
        image_list = page.get_images()
        if image_list:
            print(f"   Page {page_num + 1}: {len(image_list)} images")
            for img_idx, img in enumerate(image_list):
                xref = img[0]
                try:
                    base_image = doc.extract_image(xref)
                    pymupdf_images.append({
                        'page': page_num + 1,
                        'xref': xref,
                        'ext': base_image['ext'],
                        'size': len(base_image['image']),
                        'width': base_image.get('width', 'N/A'),
                        'height': base_image.get('height', 'N/A')
                    })
                    print(f"     Image {img_idx + 1}: xref={xref}, ext={base_image['ext']}, "
                          f"size={len(base_image['image'])} bytes")
                except Exception as e:
                    print(f"     Image {img_idx + 1}: Failed to extract - {e}")
    
    doc.close()
    print(f"\n   Total images from PyMuPDF: {len(pymupdf_images)}")
    
    # Test 5: Check if image files were saved
    print("\n5. Checking for saved image files:")
    pdf_dir = pdf_path.parent
    pdf_name = pdf_path.stem
    
    # Look for images with various patterns
    patterns = [
        f"{pdf_name}*.png",
        f"{pdf_name}*.jpg",
        f"{pdf_path.name}*.png",
        f"{pdf_path.name}*.jpg",
        "*.png",  # All PNGs in directory
    ]
    
    found_files = []
    for pattern in patterns:
        images = list(pdf_dir.glob(pattern))
        if images:
            print(f"   Found with pattern '{pattern}': {len(images)} files")
            for img in images[:5]:
                print(f"     - {img.name} ({img.stat().st_size} bytes)")
                found_files.append(str(img))
    
    if not found_files:
        print("   No image files found on disk")
    
    # Compare image counts
    print("\n6. Image count comparison:")
    print(f"   Markdown references (write_images=True): {len(img_refs_with)}")
    print(f"   page_chunks images field: {total_images}")
    print(f"   PyMuPDF direct extraction: {len(pymupdf_images)}")
    print(f"   Files on disk: {len(found_files)}")
    
    image_info = {
        'markdown_refs': len(img_refs_with),
        'page_chunks_images': total_images,
        'pymupdf_images': len(pymupdf_images),
        'files_on_disk': len(found_files),
        'images_by_page': images_by_page[:5]  # First 5
    }
    
    return image_info


def test_table_structure_analysis(pdf_path: Path):
    """Analyze table structure in detail."""
    print("\n" + "="*60)
    print("[Test] Table Structure Analysis")
    print("="*60)
    
    page_chunks = pymupdf4llm.to_markdown(str(pdf_path), page_chunks=True)
    
    # Find first page with tables
    first_table_chunk = None
    for chunk in page_chunks:
        if chunk.get('tables') and len(chunk['tables']) > 0:
            first_table_chunk = chunk
            break
    
    if not first_table_chunk:
        print("   No tables found in page_chunks")
        return None
    
    print(f"\n   First table found on page {first_table_chunk['metadata']['page']}")
    first_table = first_table_chunk['tables'][0]
    
    print(f"\n   Table structure analysis:")
    print(f"   Type: {type(first_table)}")
    
    if isinstance(first_table, dict):
        print(f"   Keys: {list(first_table.keys())}")
        
        # Try to find markdown content
        for key in ['markdown', 'text', 'content', 'html', 'md']:
            if key in first_table:
                value = first_table[key]
                if isinstance(value, str):
                    print(f"\n   {key} field (first 500 chars):")
                    print(f"   {value[:500]}...")
                    return {
                        'has_markdown': True,
                        'markdown_field': key,
                        'markdown_preview': value[:500]
                    }
        
        # Try to find structured data
        for key in ['cells', 'rows', 'data', 'table']:
            if key in first_table:
                value = first_table[key]
                print(f"\n   {key} field:")
                print(f"   Type: {type(value)}")
                if isinstance(value, list):
                    print(f"   Length: {len(value)}")
                    if len(value) > 0:
                        print(f"   First item: {value[0]}")
                elif isinstance(value, dict):
                    print(f"   Keys: {list(value.keys())}")
    
    # Also check if table appears in markdown text
    page_text = first_table_chunk.get('text', '')
    table_pattern = r'(\|[^\n]+\|\n\|[:\s\-]+\|\n(?:\|[^\n]+\|\n?)+)'
    table_matches = list(re.finditer(table_pattern, page_text, re.MULTILINE))
    
    if table_matches:
        print(f"\n   Table also found in markdown text:")
        print(f"   {table_matches[0].group(1)[:300]}...")
        return {
            'has_markdown': True,
            'markdown_in_text': True,
            'markdown_preview': table_matches[0].group(1)[:300]
        }
    
    return None


def main():
    # Convert file:// URL to Windows path
    if len(sys.argv) < 2:
        pdf_path_str = "file:///C:/Users/Harry/Documents/job/Advantest/digital_test_fundemantal/%E5%AE%9E%E9%AA%8C/SN74HC163DataSheet.pdf"
    else:
        pdf_path_str = sys.argv[1]
    
    # Handle file:// URL
    if pdf_path_str.startswith("file:///"):
        pdf_path_str = pdf_path_str[8:]  # Remove file:///
        # Decode URL encoding
        import urllib.parse
        pdf_path_str = urllib.parse.unquote(pdf_path_str)
    
    pdf_path = Path(pdf_path_str)
    
    if not pdf_path.exists():
        print(f"[ERROR] PDF file not found: {pdf_path}")
        print(f"   Resolved path: {pdf_path.resolve()}")
        sys.exit(1)
    
    print("="*60)
    print("pymupdf4llm Table and Image Extraction Test")
    print("="*60)
    print(f"PDF file: {pdf_path}")
    print(f"File size: {pdf_path.stat().st_size / 1024:.2f} KB")
    
    # Run tests
    table_info = test_table_extraction_detailed(pdf_path)
    image_info = test_image_extraction_detailed(pdf_path)
    table_structure = test_table_structure_analysis(pdf_path)
    
    # Save results
    results = {
        'pdf_path': str(pdf_path),
        'table_info': table_info,
        'image_info': image_info,
        'table_structure': table_structure
    }
    
    output_file = pdf_path.parent / f"{pdf_path.stem}_table_image_test.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False, default=str)
    
    print("\n" + "="*60)
    print("Test Complete")
    print("="*60)
    print(f"\nResults saved to: {output_file}")
    
    # Summary
    print("\n" + "="*60)
    print("Summary")
    print("="*60)
    print(f"Tables found:")
    print(f"  - In markdown: {table_info.get('markdown_tables', 0)}")
    print(f"  - In page_chunks: {table_info.get('page_chunks_tables', 0)}")
    print(f"\nImages found:")
    print(f"  - Markdown references: {image_info.get('markdown_refs', 0)}")
    print(f"  - page_chunks images: {image_info.get('page_chunks_images', 0)}")
    print(f"  - PyMuPDF extraction: {image_info.get('pymupdf_images', 0)}")
    print(f"  - Files on disk: {image_info.get('files_on_disk', 0)}")


if __name__ == "__main__":
    main()

