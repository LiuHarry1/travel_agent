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

    md_text = pymupdf4llm.to_markdown(pdf_path, page_chunks=True, write_images=True,)

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

        
    except Exception as e:
        print(f"✗ 测试失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
   
    # pdf_path = "/Users/harry/Documents/cv/刘浩的简历.pdf"
    pdf_path = "/Users/harry/Documents/复旦论文/基于Word2Vec,LSTMs和Attention机制的中文情感分析研究.pdf"

    
    # test_pymupdf4llm(pdf_path)
    test_pymupdf4llm_page_chunks(pdf_path)