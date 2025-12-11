"""Document loaders."""
from .base import BaseLoader
from .factory import LoaderFactory
from .pdf.pdf_loader import PDFLoader
from .docx.docx_loader import DOCXLoader
from .html.html_loader import HTMLLoader
from .markdown.markdown_loader import MarkdownLoader
from .txt.txt_loader import TXTLoader

__all__ = [
    "BaseLoader",
    "LoaderFactory",
    "PDFLoader",
    "DOCXLoader",
    "HTMLLoader",
    "MarkdownLoader",
    "TXTLoader",
]

