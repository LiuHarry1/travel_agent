#!/usr/bin/env python3
"""Comprehensive test for pymupdf4llm functionality."""
import sys
from pathlib import Path
import re
from typing import List, Dict, Any

# Check if pymupdf4llm is installed
try:
    import pymupdf4llm
    import fitz  # PyMuPDF
    print("✓ pymupdf4llm and PyMuPDF are installed")
except ImportError as e:
    print(f"✗ Missing dependencies: {e}")
    print("Please install: pip install pymupdf4llm")
    sys.exit(1)


def test_basic_markdown_conversion(pdf_path: Path) -> Dict[str, Any]:
    """Test 1: Basic Markdown conversion."""
    print("\n" + "="*60)
    print("[Test 1] Basic Markdown Conversion")
    print("="*60)
    
    try:
        md_text = pymupdf4llm.to_markdown(str(pdf_path))
        
        result = {
            "success": True,
            "length": len(md_text),
            "has_content": len(md_text.strip()) > 0,
            "preview": md_text[:500] if len(md_text) > 500 else md_text
        }
        
        print(f"✓ Successfully converted to Markdown")
        print(f"  - Length: {result['length']} characters")
        print(f"  - Has content: {result['has_content']}")
        print(f"  - Preview (first 500 chars):")
        print(f"    {result['preview']}...")
        
        return result
    except Exception as e:
        print(f"✗ Failed: {e}")
        import traceback
        traceback.print_exc()
        return {"success": False, "error": str(e)}


def test_page_chunks(pdf_path: Path) -> Dict[str, Any]:
    """Test 2: Page chunks functionality."""
    print("\n" + "="*60)
    print("[Test 2] Page Chunks Functionality")
    print("="*60)
    
    try:
        page_chunks = pymupdf4llm.to_markdown(str(pdf_path), page_chunks=True)
        
        result = {
            "success": True,
            "is_list": isinstance(page_chunks, list),
            "num_pages": len(page_chunks) if isinstance(page_chunks, list) else 0,
            "sample_structure": None
        }
        
        if isinstance(page_chunks, list) and len(page_chunks) > 0:
            first_chunk = page_chunks[0]
            result["sample_structure"] = {
                "type": type(first_chunk).__name__,
                "keys": list(first_chunk.keys()) if isinstance(first_chunk, dict) else None,
                "has_page_number": isinstance(first_chunk, dict) and "page_number" in first_chunk,
                "has_markdown": isinstance(first_chunk, dict) and "markdown" in first_chunk,
                "has_content": isinstance(first_chunk, dict) and "content" in first_chunk,
            }
            
            # Check page number format (0-based or 1-based)
            if isinstance(first_chunk, dict):
                page_num = first_chunk.get("page_number", first_chunk.get("page", None))
                result["page_index_format"] = "0-based" if page_num == 0 else "1-based" if page_num == 1 else "unknown"
                result["first_page_number"] = page_num
                
                # Get content field name
                content_field = None
                for key in ["markdown", "content", "text"]:
                    if key in first_chunk:
                        content_field = key
                        break
                result["content_field_name"] = content_field
                if content_field:
                    result["first_page_content_length"] = len(str(first_chunk[content_field]))
        
        print(f"✓ Page chunks retrieved")
        print(f"  - Is list: {result['is_list']}")
        print(f"  - Number of pages: {result['num_pages']}")
        if result['sample_structure']:
            print(f"  - Sample structure: {result['sample_structure']}")
            if result.get('page_index_format'):
                print(f"  - Page index format: {result['page_index_format']}")
            if result.get('content_field_name'):
                print(f"  - Content field name: {result['content_field_name']}")
        
        return result
    except Exception as e:
        print(f"✗ Failed: {e}")
        import traceback
        traceback.print_exc()
        return {"success": False, "error": str(e)}


def test_image_extraction(pdf_path: Path) -> Dict[str, Any]:
    """Test 3: Image extraction."""
    print("\n" + "="*60)
    print("[Test 3] Image Extraction")
    print("="*60)
    
    try:
        # Test with write_images=True
        md_text = pymupdf4llm.to_markdown(str(pdf_path), write_images=True)
        
        # Check for image references in markdown
        img_patterns = [
            r'!\[.*?\]\((.*?)\)',  # Markdown image syntax
            r'<img[^>]+src=["\'](.*?)["\']',  # HTML img tag
        ]
        
        image_refs = []
        for pattern in img_patterns:
            matches = re.findall(pattern, md_text, re.IGNORECASE)
            image_refs.extend(matches)
        
        # Check if images were saved to disk
        pdf_dir = pdf_path.parent
        image_files = list(pdf_dir.glob(f"{pdf_path.stem}*.png"))
        image_files.extend(pdf_dir.glob(f"{pdf_path.stem}*.jpg"))
        image_files.extend(pdf_dir.glob(f"{pdf_path.stem}*.jpeg"))
        
        result = {
            "success": True,
            "has_image_refs": len(image_refs) > 0,
            "num_image_refs": len(image_refs),
            "image_refs": image_refs[:5],  # First 5
            "has_image_files": len(image_files) > 0,
            "num_image_files": len(image_files),
            "image_files": [str(f.name) for f in image_files[:5]]
        }
        
        print(f"✓ Image extraction test completed")
        print(f"  - Image references in markdown: {result['num_image_refs']}")
        if result['image_refs']:
            print(f"  - Sample references: {result['image_refs']}")
        print(f"  - Image files on disk: {result['num_image_files']}")
        if result['image_files']:
            print(f"  - Sample files: {result['image_files']}")
        
        return result
    except Exception as e:
        print(f"✗ Failed: {e}")
        import traceback
        traceback.print_exc()
        return {"success": False, "error": str(e)}


def test_page_selection(pdf_path: Path) -> Dict[str, Any]:
    """Test 4: Page selection."""
    print("\n" + "="*60)
    print("[Test 4] Page Selection")
    print("="*60)
    
    try:
        # Test selecting first 2 pages (0-indexed)
        md_text = pymupdf4llm.to_markdown(str(pdf_path), pages=[0, 1])
        
        result = {
            "success": True,
            "length": len(md_text),
            "pages_param_works": True,
            "preview": md_text[:300] if len(md_text) > 300 else md_text
        }
        
        print(f"✓ Page selection test completed")
        print(f"  - Selected pages [0, 1]")
        print(f"  - Output length: {result['length']} characters")
        print(f"  - Preview: {result['preview']}...")
        
        return result
    except Exception as e:
        print(f"✗ Failed: {e}")
        import traceback
        traceback.print_exc()
        return {"success": False, "error": str(e)}


def test_metadata_extraction(pdf_path: Path) -> Dict[str, Any]:
    """Test 5: Metadata extraction using PyMuPDF."""
    print("\n" + "="*60)
    print("[Test 5] Metadata Extraction")
    print("="*60)
    
    try:
        doc = fitz.open(str(pdf_path))
        metadata = doc.metadata
        total_pages = len(doc)
        doc.close()
        
        result = {
            "success": True,
            "total_pages": total_pages,
            "metadata": {
                "title": metadata.get("title", ""),
                "author": metadata.get("author", ""),
                "subject": metadata.get("subject", ""),
                "creator": metadata.get("creator", ""),
                "producer": metadata.get("producer", ""),
            },
            "has_metadata": bool(metadata.get("title") or metadata.get("author"))
        }
        
        print(f"✓ Metadata extraction completed")
        print(f"  - Total pages: {result['total_pages']}")
        print(f"  - Title: {result['metadata']['title'] or '(empty)'}")
        print(f"  - Author: {result['metadata']['author'] or '(empty)'}")
        print(f"  - Subject: {result['metadata']['subject'] or '(empty)'}")
        print(f"  - Creator: {result['metadata']['creator'] or '(empty)'}")
        
        return result
    except Exception as e:
        print(f"✗ Failed: {e}")
        import traceback
        traceback.print_exc()
        return {"success": False, "error": str(e)}


def test_table_detection(pdf_path: Path) -> Dict[str, Any]:
    """Test 6: Table detection in Markdown."""
    print("\n" + "="*60)
    print("[Test 6] Table Detection")
    print("="*60)
    
    try:
        md_text = pymupdf4llm.to_markdown(str(pdf_path))
        
        # Markdown table pattern: | col1 | col2 |
        #                        |------|------|
        #                        | data | data |
        table_pattern = r'(\|[^\n]+\|\n\|[:\s\-]+\|\n(?:\|[^\n]+\|\n?)+)'
        table_matches = list(re.finditer(table_pattern, md_text, re.MULTILINE))
        
        # Count table rows
        table_rows = []
        for match in table_matches:
            table_text = match.group(1)
            rows = [r.strip() for r in table_text.split('\n') 
                   if r.strip() and r.strip().startswith('|')]
            # Exclude separator row
            data_rows = [r for r in rows if not re.match(r'^\|[\s\-:]+\|$', r.strip())]
            table_rows.append(len(data_rows))
        
        result = {
            "success": True,
            "has_tables": len(table_matches) > 0,
            "num_tables": len(table_matches),
            "table_rows": table_rows,
            "sample_table": table_matches[0].group(1)[:200] if table_matches else None
        }
        
        print(f"✓ Table detection completed")
        print(f"  - Has tables: {result['has_tables']}")
        print(f"  - Number of tables: {result['num_tables']}")
        if result['table_rows']:
            print(f"  - Rows per table: {result['table_rows']}")
        if result['sample_table']:
            print(f"  - Sample table (first 200 chars):")
            print(f"    {result['sample_table']}...")
        
        return result
    except Exception as e:
        print(f"✗ Failed: {e}")
        import traceback
        traceback.print_exc()
        return {"success": False, "error": str(e)}


def test_heading_detection(pdf_path: Path) -> Dict[str, Any]:
    """Test 7: Heading detection in Markdown."""
    print("\n" + "="*60)
    print("[Test 7] Heading Detection")
    print("="*60)
    
    try:
        md_text = pymupdf4llm.to_markdown(str(pdf_path))
        
        # Markdown heading pattern: # Heading, ## Subheading, etc.
        heading_pattern = r'^(#{1,6})\s+(.+)$'
        headings = []
        for match in re.finditer(heading_pattern, md_text, re.MULTILINE):
            level = len(match.group(1))
            text = match.group(2).strip()
            headings.append({"level": level, "text": text})
        
        # Count by level
        level_counts = {}
        for h in headings:
            level = h["level"]
            level_counts[level] = level_counts.get(level, 0) + 1
        
        result = {
            "success": True,
            "has_headings": len(headings) > 0,
            "num_headings": len(headings),
            "level_counts": level_counts,
            "sample_headings": headings[:10]  # First 10
        }
        
        print(f"✓ Heading detection completed")
        print(f"  - Has headings: {result['has_headings']}")
        print(f"  - Total headings: {result['num_headings']}")
        print(f"  - By level: {result['level_counts']}")
        if result['sample_headings']:
            print(f"  - Sample headings:")
            for h in result['sample_headings'][:5]:
                print(f"    {'#' * h['level']} {h['text']}")
        
        return result
    except Exception as e:
        print(f"✗ Failed: {e}")
        import traceback
        traceback.print_exc()
        return {"success": False, "error": str(e)}


def test_llama_reader(pdf_path: Path) -> Dict[str, Any]:
    """Test 8: LlamaMarkdownReader (optional)."""
    print("\n" + "="*60)
    print("[Test 8] LlamaMarkdownReader")
    print("="*60)
    
    try:
        llama_reader = pymupdf4llm.LlamaMarkdownReader()
        llama_docs = llama_reader.load_data(str(pdf_path))
        
        result = {
            "success": True,
            "is_list": isinstance(llama_docs, list),
            "num_docs": len(llama_docs) if isinstance(llama_docs, list) else 0,
            "sample_doc_structure": None
        }
        
        if isinstance(llama_docs, list) and len(llama_docs) > 0:
            first_doc = llama_docs[0]
            # Check if it's a LlamaIndex Document
            result["sample_doc_structure"] = {
                "type": type(first_doc).__name__,
                "has_text": hasattr(first_doc, "text") or hasattr(first_doc, "get_content"),
                "has_metadata": hasattr(first_doc, "metadata"),
            }
            if hasattr(first_doc, "text"):
                result["first_doc_text_length"] = len(first_doc.text)
            elif hasattr(first_doc, "get_content"):
                result["first_doc_text_length"] = len(first_doc.get_content())
        
        print(f"✓ LlamaMarkdownReader test completed")
        print(f"  - Is list: {result['is_list']}")
        print(f"  - Number of documents: {result['num_docs']}")
        if result['sample_doc_structure']:
            print(f"  - Sample structure: {result['sample_doc_structure']}")
        
        return result
    except Exception as e:
        print(f"⚠ LlamaMarkdownReader not available or failed: {e}")
        return {"success": False, "error": str(e), "optional": True}


def main():
    """Run all tests."""
    if len(sys.argv) < 2:
        print("Usage: python test_pymupdf4llm_comprehensive.py <pdf_path>")
        print("\nExample:")
        print("  python test_pymupdf4llm_comprehensive.py static/sources/sample.pdf")
        sys.exit(1)
    
    pdf_path = Path(sys.argv[1])
    
    if not pdf_path.exists():
        print(f"✗ PDF file not found: {pdf_path}")
        sys.exit(1)
    
    print("\n" + "="*60)
    print("Comprehensive pymupdf4llm Test Suite")
    print("="*60)
    print(f"PDF file: {pdf_path}")
    print(f"File size: {pdf_path.stat().st_size / 1024:.2f} KB")
    
    results = {}
    
    # Run all tests
    results["basic_markdown"] = test_basic_markdown_conversion(pdf_path)
    results["page_chunks"] = test_page_chunks(pdf_path)
    results["image_extraction"] = test_image_extraction(pdf_path)
    results["page_selection"] = test_page_selection(pdf_path)
    results["metadata"] = test_metadata_extraction(pdf_path)
    results["tables"] = test_table_detection(pdf_path)
    results["headings"] = test_heading_detection(pdf_path)
    results["llama_reader"] = test_llama_reader(pdf_path)
    
    # Summary
    print("\n" + "="*60)
    print("Test Summary")
    print("="*60)
    
    for test_name, result in results.items():
        status = "✓" if result.get("success") else "✗"
        optional = " (optional)" if result.get("optional") else ""
        print(f"{status} {test_name}: {result.get('success', False)}{optional}")
    
    # Save results to file
    output_file = pdf_path.parent / f"{pdf_path.stem}_test_results.md"
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(f"# Test Results for {pdf_path.name}\n\n")
        f.write(f"## Summary\n\n")
        for test_name, result in results.items():
            status = "✓" if result.get("success") else "✗"
            f.write(f"- {status} {test_name}\n")
        f.write(f"\n## Detailed Results\n\n")
        for test_name, result in results.items():
            f.write(f"### {test_name}\n\n")
            f.write(f"```json\n{result}\n```\n\n")
    
    print(f"\n✓ Detailed results saved to: {output_file}")
    print("="*60 + "\n")


if __name__ == "__main__":
    main()

