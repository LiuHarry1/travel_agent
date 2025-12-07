"""Retrieval API schemas."""
from pydantic import BaseModel
from typing import List, Dict, Any, Optional


class QueryRequest(BaseModel):
    """Query request model."""
    query: str
    pipeline_name: Optional[str] = None


class ChunkResult(BaseModel):
    """Chunk result model."""
    chunk_id: int
    text: str


class RetrievalResponse(BaseModel):
    """Retrieval response model."""
    query: str
    results: List[ChunkResult]


class DebugChunkResult(BaseModel):
    """Debug chunk result with scores."""
    chunk_id: int
    text: str
    score: Optional[float] = None
    rerank_score: Optional[float] = None
    embedder: Optional[str] = None


class DebugRetrievalResponse(BaseModel):
    """Debug retrieval response with all steps."""
    query: str
    results: List[ChunkResult]
    debug: Dict[str, Any]

