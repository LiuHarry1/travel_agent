"""LangChain utilities for text chunking."""
try:
    from langchain_text_splitters import RecursiveCharacterTextSplitter
except ImportError:
    # Fallback for older langchain versions
    from langchain.text_splitter import RecursiveCharacterTextSplitter
from typing import List, Optional


def create_tiktoken_splitter(
    chunk_size: int = 1000,
    chunk_overlap: int = 200,
    encoding_name: str = "cl100k_base",
    separators: Optional[List[str]] = None
) -> RecursiveCharacterTextSplitter:
    """
    Create a RecursiveCharacterTextSplitter using tiktoken encoder.
    
    Args:
        chunk_size: Maximum size of chunks (in tokens)
        chunk_overlap: Overlap between chunks (in tokens)
        encoding_name: Tiktoken encoding name (default: "cl100k_base")
        separators: Custom separators list. If None, uses default.
    
    Returns:
        RecursiveCharacterTextSplitter instance configured with tiktoken
    """
    if separators is None:
        separators = ["\n\n\n", "\n\n", "\n", ". ", "。", "！", "？", " ", ""]
    
    return RecursiveCharacterTextSplitter.from_tiktoken_encoder(
        encoding_name=encoding_name,
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=separators
    )

