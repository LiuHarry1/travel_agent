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
class CacheConfig:
    """Cache configuration for RAG results."""
    enabled: bool = True
    ttl_seconds: int = 300  # Time to live in seconds
    max_size: int = 1000  # Maximum number of cache entries


@dataclass
class ProcessorConfig:
    """Result processor configuration."""
    ranking_strategy: str = "score"  # "score" or "round"
    merge_keep_best_score: bool = True  # Keep best score when merging duplicates


@dataclass
class InputGuardrailConfig:
    """Input guardrail configuration."""
    enabled: bool = True
    strict_mode: bool = False  # True: reject on failure, False: sanitize and continue
    max_query_length: int = 1000  # Maximum query length
    blocked_patterns: List[str] = field(default_factory=list)  # Patterns to block
    sensitive_patterns: List[str] = field(default_factory=list)  # Sensitive info patterns


@dataclass
class OutputGuardrailConfig:
    """Output guardrail configuration."""
    enabled: bool = True
    strict_mode: bool = False  # True: reject on failure, False: filter and continue
    max_results: int = 50  # Maximum number of results to return
    filter_sensitive_info: bool = True  # Filter sensitive information from results
    validate_relevance: bool = True  # Validate result relevance
    sensitive_patterns: List[str] = field(default_factory=list)  # Sensitive info patterns


@dataclass
class RetrievalSourceConfig:
    """Retrieval source configuration."""
    type: str  # "retrieval_service", "local", etc.
    enabled: bool = True
    url: Optional[str] = None
    pipeline_name: str = "default"
    timeout: float = 60.0  # Request timeout in seconds
    config: Dict = field(default_factory=dict)


@dataclass
class RAGConfig:
    """RAG system configuration."""
    enabled: bool = True
    strategy: str = "multi_round"  # "single_round", "multi_round", "parallel"
    max_rounds: int = 3
    query_rewriter: QueryRewriterConfig = field(default_factory=QueryRewriterConfig)
    sources: List[RetrievalSourceConfig] = field(default_factory=list)
    cache: Optional[CacheConfig] = None
    processor: ProcessorConfig = field(default_factory=ProcessorConfig)
    input_guardrail: InputGuardrailConfig = field(default_factory=InputGuardrailConfig)
    output_guardrail: OutputGuardrailConfig = field(default_factory=OutputGuardrailConfig)
    fallback_on_error: bool = True  # Return empty results on error instead of raising
    
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
                timeout=src.get("timeout", 60.0),
                config=src.get("config", {})
            )
            for src in sources_data
        ]
        
        # Parse cache config
        cache_data = data.get("cache", {})
        cache = None
        if cache_data.get("enabled", True):
            cache = CacheConfig(
                enabled=cache_data.get("enabled", True),
                ttl_seconds=cache_data.get("ttl_seconds", 300),
                max_size=cache_data.get("max_size", 1000)
            )
        
        # Parse processor config
        processor_data = data.get("processor", {})
        processor = ProcessorConfig(
            ranking_strategy=processor_data.get("ranking_strategy", "score"),
            merge_keep_best_score=processor_data.get("merge_keep_best_score", True)
        )
        
        # Parse input guardrail config
        input_guardrail_data = data.get("input_guardrail", {})
        input_guardrail = InputGuardrailConfig(
            enabled=input_guardrail_data.get("enabled", True),
            strict_mode=input_guardrail_data.get("strict_mode", False),
            max_query_length=input_guardrail_data.get("max_query_length", 1000),
            blocked_patterns=input_guardrail_data.get("blocked_patterns", []),
            sensitive_patterns=input_guardrail_data.get("sensitive_patterns", [])
        )
        
        # Parse output guardrail config
        output_guardrail_data = data.get("output_guardrail", {})
        output_guardrail = OutputGuardrailConfig(
            enabled=output_guardrail_data.get("enabled", True),
            strict_mode=output_guardrail_data.get("strict_mode", False),
            max_results=output_guardrail_data.get("max_results", 50),
            filter_sensitive_info=output_guardrail_data.get("filter_sensitive_info", True),
            validate_relevance=output_guardrail_data.get("validate_relevance", True),
            sensitive_patterns=output_guardrail_data.get("sensitive_patterns", [])
        )
        
        return cls(
            enabled=data.get("enabled", True),
            strategy=data.get("strategy", "multi_round"),
            max_rounds=data.get("max_rounds", 3),
            query_rewriter=query_rewriter,
            sources=sources,
            cache=cache,
            processor=processor,
            input_guardrail=input_guardrail,
            output_guardrail=output_guardrail,
            fallback_on_error=data.get("fallback_on_error", True)
        )

