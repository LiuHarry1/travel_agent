"""LangChain utilities for text chunking."""
try:
    from langchain_text_splitters import RecursiveCharacterTextSplitter, MarkdownHeaderTextSplitter
except ImportError:
    # Fallback for older langchain versions
    from langchain.text_splitter import RecursiveCharacterTextSplitter
    try:
        from langchain_text_splitters import MarkdownHeaderTextSplitter
    except ImportError:
        MarkdownHeaderTextSplitter = None
from typing import List, Optional, Tuple


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


def create_markdown_header_splitter(
    headers_to_split_on: Optional[List[Tuple[str, str]]] = None
) -> MarkdownHeaderTextSplitter:
    """
    Create MarkdownHeaderTextSplitter with all header levels.
    
    Args:
        headers_to_split_on: List of tuples (header_marker, header_name).
                            If None, uses all levels (# to ######).
    
    Returns:
        MarkdownHeaderTextSplitter instance
    """
    if MarkdownHeaderTextSplitter is None:
        raise ImportError(
            "MarkdownHeaderTextSplitter is not available. "
            "Please install langchain-text-splitters>=0.0.1"
        )
    
    if headers_to_split_on is None:
        headers_to_split_on = [
            ("#", "Header 1"),
            ("##", "Header 2"),
            ("###", "Header 3"),
            ("####", "Header 4"),
            ("#####", "Header 5"),
            ("######", "Header 6"),
        ]
    
    return MarkdownHeaderTextSplitter(
        headers_to_split_on=headers_to_split_on,
        strip_headers=False
    )

