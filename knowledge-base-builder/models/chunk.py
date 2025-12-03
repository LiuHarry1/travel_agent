"""Chunk model."""
from dataclasses import dataclass
from typing import Dict, Any, Optional


@dataclass
class Chunk:
    """Text chunk model."""
    text: str
    chunk_id: str
    document_id: str
    chunk_index: int
    metadata: Dict[str, Any] = None
    embedding: Optional[list] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}

