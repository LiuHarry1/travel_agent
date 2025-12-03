"""Markdown document loader."""
from pathlib import Path
from typing import Dict, Any
from .base import BaseLoader
from ...models.document import Document, DocumentType
from ...utils.exceptions import LoaderError


class MarkdownLoader(BaseLoader):
    """Loads markdown files."""
    
    def load(self, source: str, **kwargs) -> Document:
        """Load markdown file."""
        try:
            path = Path(source)
            if not path.exists():
                raise FileNotFoundError(f"File not found: {source}")
            
            content = path.read_text(encoding="utf-8")
            metadata = {
                "file_path": str(path),
                "file_name": path.name,
                "file_size": path.stat().st_size,
                **kwargs.get("metadata", {})
            }
            
            return Document(
                content=content,
                source=str(path),
                doc_type=DocumentType.MARKDOWN,
                metadata=metadata
            )
        except Exception as e:
            raise LoaderError(f"Failed to load markdown file: {str(e)}") from e
    
    def supports(self, doc_type: DocumentType) -> bool:
        """Check if supports markdown."""
        return doc_type == DocumentType.MARKDOWN

