"""RAG configuration."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class QueryRewriterConfig:
    """Query rewriter configuration."""
    enabled: bool = True
    model: Optional[str] = None  # If None, uses default LLM from config


@dataclass
class RetrievalSourceConfig:
    """Retrieval source configuration."""
    type: str  # "retrieval_service", "local", etc.
    enabled: bool = True
    url: Optional[str] = None
    pipeline_name: str = "default"
    config: Dict = field(default_factory=dict)


@dataclass
class RAGConfig:
    """RAG system configuration."""
    enabled: bool = True
    strategy: str = "multi_round"  # "single_round", "multi_round", "parallel"
    max_rounds: int = 3
    query_rewriter: QueryRewriterConfig = field(default_factory=QueryRewriterConfig)
    sources: List[RetrievalSourceConfig] = field(default_factory=list)
    
    @classmethod
    def from_dict(cls, data: Dict) -> RAGConfig:
        """Create RAGConfig from dictionary."""
        query_rewriter_data = data.get("query_rewriter", {})
        query_rewriter = QueryRewriterConfig(
            enabled=query_rewriter_data.get("enabled", True),
            model=query_rewriter_data.get("model")
        )
        
        sources_data = data.get("sources", [])
        sources = [
            RetrievalSourceConfig(
                type=src.get("type"),
                enabled=src.get("enabled", True),
                url=src.get("url"),
                pipeline_name=src.get("pipeline_name", "default"),
                config=src.get("config", {})
            )
            for src in sources_data
        ]
        
        return cls(
            enabled=data.get("enabled", True),
            strategy=data.get("strategy", "multi_round"),
            max_rounds=data.get("max_rounds", 3),
            query_rewriter=query_rewriter,
            sources=sources
        )

