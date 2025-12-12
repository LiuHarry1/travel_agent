#!/usr/bin/env python3
"""测试 PyMuPDF4LLM 是否能满足当前 PDF loader 的需求"""
import sys
from pathlib import Path
import re

 # 检查是否安装了 pymupdf4llm
try:
    import pymupdf4llm
    print("✓ PyMuPDF4LLM 已安装")
except ImportError:
    print("✗ PyMuPDF4LLM 未安装，请运行: pip install pymupdf4llm")
    

def test_pymupdf4llm_page_chunks(pdf_path: str):

    md_text = pymupdf4llm.to_markdown(pdf_path, page_chunks=True, write_images=True)

    print(f"✓ 输出已保存到: {md_text}")

def test_pymupdf4llm(pdf_path: str):
    """测试 PyMuPDF4LLM 的基本功能"""
    
    print(f"\n{'='*60}")
    print(f"测试 PyMuPDF4LLM 功能")
    print(f"PDF 文件: {pdf_path}")
    print(f"{'='*60}\n")
    
   
    
    pdf_path = Path(pdf_path)
    if not pdf_path.exists():
        print(f"✗ PDF 文件不存在: {pdf_path}")
        return
    
    try:
        # 测试 1: 基本转换
        print("\n[测试 1] 基本 Markdown 转换")
        md_text = pymupdf4llm.to_markdown(pdf_path,  page_chunks=True, write_images=True,)
        print(f"✓ 成功提取 Markdown，长度: {len(md_text)} 字符")

        with open("output.md", "w", encoding="utf-8") as f:
            f.write(md_text)
        
        # 测试 2: 检查页面标记（当前 loader 需要 <page> 标签）
        print("\n[测试 2] 页面标记检查")
        has_page_tags = '<page' in md_text.lower() or 'page' in md_text.lower()
        print(f"{'✓' if has_page_tags else '✗'} 页面标记: {has_page_tags}")
        
        # 测试 3: 检查表格（当前 loader 需要 <table> 标签）
        print("\n[测试 3] 表格检查")
        has_table_tags = '<table' in md_text.lower()
        has_markdown_tables = '|' in md_text and '---' in md_text
        print(f"{'✓' if has_table_tags or has_markdown_tables else '✗'} 表格提取: {has_table_tags or has_markdown_tables}")
        if has_markdown_tables:
            table_count = len(re.findall(r'\|.*\|', md_text))
            print(f"  找到约 {table_count} 个表格行")
        
        # 测试 4: 检查图片（当前 loader 需要 <img> 标签或图片引用）
        print("\n[测试 4] 图片检查")
        has_img_tags = '<img' in md_text.lower() or '![' in md_text
        print(f"{'✓' if has_img_tags else '✗'} 图片提取: {has_img_tags}")
        if has_img_tags:
            img_count = len(re.findall(r'<img|!\[', md_text, re.IGNORECASE))
            print(f"  找到约 {img_count} 个图片引用")
        
        # 测试 5: 检查元数据
        print("\n[测试 5] PDF 元数据检查")
        try:
            import fitz
            doc = fitz.open(pdf_path)
            metadata = doc.metadata
            doc.close()
            has_metadata = bool(metadata.get('title') or metadata.get('author'))
            print(f"{'✓' if has_metadata else '✗'} 元数据提取: {has_metadata}")
            if metadata.get('title'):
                print(f"  标题: {metadata.get('title')}")
            if metadata.get('author'):
                print(f"  作者: {metadata.get('author')}")
        except Exception as e:
            print(f"✗ 元数据提取失败: {e}")
        
        # 测试 6: 检查字符位置追踪（当前 chunker 需要）
        print("\n[测试 6] 字符位置追踪检查")
        has_char_pos = 'start_char' in md_text.lower() or 'char' in md_text.lower()
        print(f"{'✓' if has_char_pos else '✗'} 字符位置信息: {has_char_pos}")
        
        # 测试 7: 输出格式检查
        print("\n[测试 7] Markdown 格式检查")
        print(f"  前 500 字符预览:")
        print(f"  {md_text[:500]}...")
        
        # 总结
        print(f"\n{'='*60}")
        print("测试总结:")
        print(f"  - Markdown 转换: ✓")
        print(f"  - 页面标记: {'✓' if has_page_tags else '⚠️  需要手动添加'}")
        print(f"  - 表格提取: {'✓' if has_table_tags or has_markdown_tables else '⚠️  可能需要处理'}")
        print(f"  - 图片提取: {'✓' if has_img_tags else '⚠️  可能需要处理'}")
        print(f"  - 元数据: {'✓' if has_metadata else '⚠️  需要单独提取'}")
        print(f"  - 字符位置: {'✓' if has_char_pos else '⚠️  需要手动计算'}")
        print(f"{'='*60}\n")
        
        # 保存输出到文件
        output_file = pdf_path.parent / f"{pdf_path.stem}_pymupdf4llm_output.md"
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(md_text)
        print(f"✓ 输出已保存到: {output_file}")
        
    except Exception as e:
        print(f"✗ 测试失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
   
    # pdf_path = "/Users/harry/Documents/cv/刘浩的简历.pdf"
    pdf_path = "/Users/harry/Documents/复旦论文/基于Word2Vec,LSTMs和Attention机制的中文情感分析研究.pdf"

    
    # test_pymupdf4llm(pdf_path)
    test_pymupdf4llm_page_chunks(pdf_path)