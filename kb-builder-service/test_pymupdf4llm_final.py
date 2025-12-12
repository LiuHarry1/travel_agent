#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Final comprehensive test for tables and images - save to JSON."""
import sys
from pathlib import Path
import re
import json
import urllib.parse

try:
    import pymupdf4llm
    import fitz  # PyMuPDF
except ImportError as e:
    print(f"ERROR: Missing dependencies: {e}")
    sys.exit(1)


def test_comprehensive(pdf_path: Path):
    """Comprehensive test - save results to JSON."""
    results = {
        'pdf_path': str(pdf_path),
        'tables': {},
        'images': {}
    }
    
    # ===== TABLE TESTING =====
    print("Testing tables...")
    
    # Full markdown
    full_md = pymupdf4llm.to_markdown(str(pdf_path))
    table_pattern = r'(\|[^\n]+\|\n\|[:\s\-]+\|\n(?:\|[^\n]+\|\n?)+)'
    md_tables = list(re.finditer(table_pattern, full_md, re.MULTILINE))
    
    # Page chunks
    page_chunks = pymupdf4llm.to_markdown(str(pdf_path), page_chunks=True)
    
    tables_info = []
    for chunk in page_chunks:
        page_num = chunk['metadata']['page']
        tables = chunk.get('tables', [])
        page_text = chunk.get('text', '')
        
        if tables:
            for table in tables:
                table_info = {
                    'page': page_num,
                    'rows': table.get('rows', 0),
                    'columns': table.get('columns', 0),
                    'bbox': str(table.get('bbox', ''))
                }
                
                # Check if table content is in markdown text
                # Look for pipe characters
                pipe_count = page_text.count('|')
                table_info['pipes_in_text'] = pipe_count
                
                # Check for standard markdown table
                md_table_matches = list(re.finditer(table_pattern, page_text, re.MULTILINE))
                table_info['markdown_tables_in_text'] = len(md_table_matches)
                
                tables_info.append(table_info)
    
    results['tables'] = {
        'markdown_tables': len(md_tables),
        'page_chunks_tables': len(tables_info),
        'tables_detail': tables_info[:10]  # First 10
    }
    
    # ===== IMAGE TESTING =====
    print("Testing images...")
    
    # With write_images
    md_with_img = pymupdf4llm.to_markdown(str(pdf_path), write_images=True)
    img_pattern = r'!\[([^\]]*)\]\(([^\)]+)\)'
    img_matches = list(re.finditer(img_pattern, md_with_img))
    
    image_refs = []
    for match in img_matches[:10]:  # First 10
        image_refs.append({
            'alt': match.group(1),
            'path': match.group(2)
        })
    
    # Page chunks images
    page_chunks_with_img = pymupdf4llm.to_markdown(str(pdf_path), page_chunks=True, write_images=True)
    images_in_chunks = 0
    for chunk in page_chunks_with_img:
        images = chunk.get('images', [])
        if images:
            images_in_chunks += len(images)
    
    # PyMuPDF direct
    doc = fitz.open(str(pdf_path))
    pymupdf_images = []
    for page_num in range(len(doc)):
        page = doc[page_num]
        image_list = page.get_images()
        if image_list:
            for img in image_list:
                xref = img[0]
                try:
                    base_image = doc.extract_image(xref)
                    pymupdf_images.append({
                        'page': page_num + 1,
                        'xref': xref,
                        'ext': base_image['ext'],
                        'size': len(base_image['image'])
                    })
                except:
                    pass
    doc.close()
    
    # Check files on disk
    pdf_dir = pdf_path.parent
    pdf_name = pdf_path.stem
    image_files = list(pdf_dir.glob(f"{pdf_name}*.png"))
    image_files.extend(pdf_dir.glob(f"{pdf_name}*.jpg"))
    
    results['images'] = {
        'markdown_refs': len(img_matches),
        'image_refs_detail': image_refs,
        'page_chunks_images': images_in_chunks,
        'pymupdf_images': len(pymupdf_images),
        'pymupdf_images_detail': pymupdf_images[:10],
        'files_on_disk': len(image_files),
        'files_on_disk_names': [f.name for f in image_files[:10]]
    }
    
    # ===== SAVE RESULTS =====
    output_file = pdf_path.parent / f"{pdf_path.stem}_final_test.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    print(f"\nResults saved to: {output_file}")
    print(f"\nSummary:")
    print(f"  Tables: {len(tables_info)} in page_chunks, {len(md_tables)} in markdown")
    print(f"  Images: {len(img_matches)} refs, {images_in_chunks} in chunks, {len(pymupdf_images)} from PyMuPDF")
    
    return results


def main():
    if len(sys.argv) < 2:
        pdf_path_str = "file:///C:/Users/Harry/Documents/job/Advantest/digital_test_fundemantal/%E5%AE%9E%E9%AA%8C/SN74HC163DataSheet.pdf"
    else:
        pdf_path_str = sys.argv[1]
    
    if pdf_path_str.startswith("file:///"):
        pdf_path_str = pdf_path_str[8:]
        pdf_path_str = urllib.parse.unquote(pdf_path_str)
    
    pdf_path = Path(pdf_path_str)
    
    if not pdf_path.exists():
        print(f"ERROR: PDF file not found: {pdf_path}")
        sys.exit(1)
    
    test_comprehensive(pdf_path)


if __name__ == "__main__":
    main()

