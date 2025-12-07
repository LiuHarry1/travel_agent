"""Chunk domain model."""
from typing import Optional
from dataclasses import dataclass


@dataclass
class Chunk:
    """Chunk entity representing a document chunk."""
    
    chunk_id: int
    text: str
    score: Optional[float] = None
    rerank_score: Optional[float] = None
    embedder: Optional[str] = None
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "chunk_id": self.chunk_id,
            "text": self.text,
            "score": self.score,
            "rerank_score": self.rerank_score,
            "embedder": self.embedder,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "Chunk":
        """Create from dictionary."""
        return cls(
            chunk_id=data["chunk_id"],
            text=data.get("text", ""),
            score=data.get("score"),
            rerank_score=data.get("rerank_score"),
            embedder=data.get("embedder"),
        )

