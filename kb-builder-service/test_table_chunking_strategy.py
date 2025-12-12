#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Test table chunking strategy and location tracking."""
import sys
from pathlib import Path
import re
import json
import urllib.parse
import fitz  # PyMuPDF
import pymupdf4llm

def analyze_table_chunking_strategy(pdf_path: Path):
    """Analyze table chunking strategy based on table size."""
    print("="*60)
    print("Table Chunking Strategy Analysis")
    print("="*60)
    
    # Get page chunks
    page_chunks = pymupdf4llm.to_markdown(str(pdf_path), page_chunks=True)
    
    # Open PDF for bbox extraction
    doc = fitz.open(str(pdf_path))
    
    results = {
        'tables_analysis': [],
        'chunking_recommendations': []
    }
    
    table_index = 0
    
    for chunk in page_chunks:
        page_num = chunk['metadata']['page']
        tables = chunk.get('tables', [])
        page_text = chunk.get('text', '')
        
        if not tables:
            continue
        
        page_obj = doc[page_num - 1]  # 0-based index
        
        for table in tables:
            rows = table.get('rows', 0)
            cols = table.get('columns', 0)
            bbox = table.get('bbox', None)
            
            # Estimate table size
            # Small: <= 10 rows, Medium: 11-30 rows, Large: > 30 rows
            if rows <= 10:
                size_category = 'small'
                chunking_strategy = 'single_chunk'
            elif rows <= 30:
                size_category = 'medium'
                chunking_strategy = 'split_by_rows'
            else:
                size_category = 'large'
                chunking_strategy = 'split_by_rows_with_header'
            
            # Try to extract table content from text using bbox
            table_content = extract_table_content_by_bbox(page_text, bbox, page_obj)
            
            # Calculate token count (estimate)
            token_count_estimate = len(table_content.split()) * 1.3  # Rough estimate
            
            table_info = {
                'table_index': table_index,
                'page': page_num,
                'rows': rows,
                'columns': cols,
                'bbox': list(bbox) if bbox else None,
                'size_category': size_category,
                'chunking_strategy': chunking_strategy,
                'token_count_estimate': int(token_count_estimate),
                'content_length': len(table_content),
                'content_preview': table_content[:200] if table_content else None
            }
            
            # Chunking recommendations
            if size_category == 'small':
                recommendation = {
                    'strategy': 'single_chunk',
                    'reason': f'Small table ({rows} rows) fits in one chunk',
                    'chunks': 1
                }
            elif size_category == 'medium':
                # Split into 2-3 chunks
                rows_per_chunk = max(5, rows // 3)
                num_chunks = (rows + rows_per_chunk - 1) // rows_per_chunk
                recommendation = {
                    'strategy': 'split_by_rows',
                    'reason': f'Medium table ({rows} rows) should be split',
                    'rows_per_chunk': rows_per_chunk,
                    'chunks': num_chunks
                }
            else:  # large
                # Split with header preservation
                rows_per_chunk = max(10, rows // 5)
                num_chunks = (rows + rows_per_chunk - 1) // rows_per_chunk
                recommendation = {
                    'strategy': 'split_by_rows_with_header',
                    'reason': f'Large table ({rows} rows) needs header preservation',
                    'rows_per_chunk': rows_per_chunk,
                    'chunks': num_chunks,
                    'preserve_header': True
                }
            
            table_info['recommendation'] = recommendation
            results['tables_analysis'].append(table_info)
            
            table_index += 1
    
    doc.close()
    
    # Summary
    print(f"\nTotal tables analyzed: {len(results['tables_analysis'])}")
    
    size_counts = {}
    for table in results['tables_analysis']:
        size = table['size_category']
        size_counts[size] = size_counts.get(size, 0) + 1
    
    print(f"\nTable size distribution:")
    for size, count in size_counts.items():
        print(f"  {size}: {count}")
    
    return results


def extract_table_content_by_bbox(page_text: str, bbox: tuple, page_obj) -> str:
    """Try to extract table content using bbox information."""
    if not bbox:
        return ""
    
    # bbox is (x0, y0, x1, y1)
    x0, y0, x1, y1 = bbox
    
    # For now, return empty - we'll need to use PyMuPDF to extract text from bbox
    # This is a placeholder - actual implementation would use page_obj.get_text("text", clip=bbox)
    try:
        # Try to extract text from bbox area
        text_in_bbox = page_obj.get_text("text", clip=fitz.Rect(x0, y0, x1, y1))
        return text_in_bbox
    except:
        return ""


def analyze_location_tracking(pdf_path: Path):
    """Analyze how to track chunk location back to PDF."""
    print("\n" + "="*60)
    print("Location Tracking Analysis")
    print("="*60)
    
    page_chunks = pymupdf4llm.to_markdown(str(pdf_path), page_chunks=True)
    doc = fitz.open(str(pdf_path))
    
    location_strategies = []
    
    for chunk in page_chunks:
        page_num = chunk['metadata']['page']
        page_text = chunk.get('text', '')
        tables = chunk.get('tables', [])
        
        # Strategy 1: Page-level location
        page_location = {
            'type': 'page',
            'page': page_num,
            'description': f'Page {page_num} of PDF'
        }
        
        # Strategy 2: Table-level location (with bbox)
        for table_idx, table in enumerate(tables):
            bbox = table.get('bbox', None)
            rows = table.get('rows', 0)
            cols = table.get('columns', 0)
            
            table_location = {
                'type': 'table',
                'page': page_num,
                'table_index': table_idx,
                'bbox': list(bbox) if bbox else None,
                'rows': rows,
                'columns': cols,
                'description': f'Table {table_idx} on page {page_num}',
                'bbox_description': f'Bbox: ({bbox[0]:.1f}, {bbox[1]:.1f}, {bbox[2]:.1f}, {bbox[3]:.1f})' if bbox else None
            }
            
            location_strategies.append(table_location)
    
    doc.close()
    
    print(f"\nLocation tracking strategies:")
    print(f"  Total tables: {len(location_strategies)}")
    
    # Show sample locations
    print(f"\n  Sample locations (first 3):")
    for loc in location_strategies[:3]:
        print(f"    {loc['description']}")
        if loc.get('bbox_description'):
            print(f"      {loc['bbox_description']}")
    
    return {
        'location_strategies': location_strategies,
        'total_tables': len(location_strategies)
    }


def design_chunk_id_schema():
    """Design chunk ID schema for table chunks."""
    print("\n" + "="*60)
    print("Chunk ID Schema Design")
    print("="*60)
    
    schemas = {
        'table_chunk_id': {
            'format': '{document_id}_table_{table_index}_chunk_{chunk_index}',
            'example': 'SN74HC163DataSheet_table_0_chunk_0',
            'components': {
                'document_id': 'PDF filename or ID',
                'table_index': 'Table index within document (0-based)',
                'chunk_index': 'Chunk index within table (0-based, for split tables)'
            }
        },
        'location_metadata': {
            'page': 'Page number (1-based)',
            'table_index': 'Table index on page',
            'bbox': 'Bounding box coordinates [x0, y0, x1, y1]',
            'row_range': 'Row range for split chunks (start, end)',
            'column_range': 'Column range if needed (start, end)'
        }
    }
    
    print("\nChunk ID Schema:")
    print(json.dumps(schemas, indent=2))
    
    return schemas


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
    
    # Run analyses
    chunking_results = analyze_table_chunking_strategy(pdf_path)
    location_results = analyze_location_tracking(pdf_path)
    chunk_id_schema = design_chunk_id_schema()
    
    # Combine results
    final_results = {
        'pdf_path': str(pdf_path),
        'chunking_analysis': chunking_results,
        'location_tracking': location_results,
        'chunk_id_schema': chunk_id_schema
    }
    
    # Save results
    output_file = pdf_path.parent / f"{pdf_path.stem}_chunking_strategy.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(final_results, f, indent=2, ensure_ascii=False, default=str)
    
    print(f"\n" + "="*60)
    print(f"Results saved to: {output_file}")
    print("="*60)


if __name__ == "__main__":
    main()

