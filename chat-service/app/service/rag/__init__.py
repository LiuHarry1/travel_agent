"""RAG (Retrieval-Augmented Generation) service module."""
from __future__ import annotations

from app.service.rag.orchestrator import RAGOrchestrator
from app.service.rag.config import RAGConfig, QueryRewriterConfig, RetrievalSourceConfig
from app.service.rag.query_rewriter import QueryRewriter
from app.service.rag.sources.base import BaseRetrievalSource, RetrievalResult
from app.service.rag.strategies.base import BaseRetrievalStrategy

__all__ = [
    "RAGOrchestrator",
    "RAGConfig",
    "QueryRewriterConfig",
    "RetrievalSourceConfig",
    "QueryRewriter",
    "BaseRetrievalSource",
    "RetrievalResult",
    "BaseRetrievalStrategy",
]

