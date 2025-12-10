"""Application settings with Pydantic validation."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml
from pydantic import BaseModel, Field, field_validator

from app.utils.constants import BACKEND_ROOT


class LLMSettings(BaseModel):
    """LLM configuration settings."""
    provider: str = Field(default="qwen", description="LLM provider name")
    model: str = Field(default="qwen-max", description="Default model name")
    timeout: float = Field(default=30.0, description="Request timeout in seconds")
    system_prompt_template: str = Field(
        default="",
        description="System prompt template. Use {tools} placeholder for available tools list."
    )
    openai_model: Optional[str] = Field(default=None, description="OpenAI model")
    
    @field_validator("system_prompt_template")
    @classmethod
    def validate_system_prompt(cls, v: str) -> str:
        """Ensure system prompt is not empty."""
        if not v or not v.strip():
            raise ValueError("system_prompt_template is required")
        return v


class RAGQueryRewriterConfig(BaseModel):
    """RAG query rewriter configuration."""
    enabled: bool = Field(default=True, description="Enable query rewriting")
    model: Optional[str] = Field(default=None, description="LLM model for rewriting (uses default if None)")


class RAGSourceConfig(BaseModel):
    """RAG retrieval source configuration."""
    type: str = Field(description="Source type: retrieval_service, local, etc.")
    enabled: bool = Field(default=True, description="Enable this source")
    url: Optional[str] = Field(default=None, description="Source URL (for retrieval_service)")
    pipeline_name: str = Field(default="default", description="Pipeline name")
    config: Dict[str, Any] = Field(default_factory=dict, description="Source-specific config")
    timeout: float = Field(default=60.0, description="Request timeout in seconds")


class RAGCacheConfig(BaseModel):
    """RAG cache configuration."""
    enabled: bool = Field(default=True, description="Enable result caching")
    ttl_seconds: int = Field(default=300, description="Cache TTL in seconds")
    max_size: int = Field(default=1000, description="Maximum cache entries")


class RAGProcessorConfig(BaseModel):
    """RAG result processor configuration."""
    ranking_strategy: str = Field(default="score", description="Ranking strategy: score or round")
    merge_keep_best_score: bool = Field(default=True, description="Keep best score when merging duplicates")


class RAGInputGuardrailConfig(BaseModel):
    """RAG input guardrail configuration."""
    enabled: bool = Field(default=True, description="Enable input guardrail")
    strict_mode: bool = Field(default=False, description="Strict mode: reject on failure")
    max_query_length: int = Field(default=1000, description="Maximum query length")
    blocked_patterns: List[str] = Field(default_factory=list, description="Blocked patterns")
    sensitive_patterns: List[str] = Field(default_factory=list, description="Sensitive info patterns")


class RAGOutputGuardrailConfig(BaseModel):
    """RAG output guardrail configuration."""
    enabled: bool = Field(default=True, description="Enable output guardrail")
    strict_mode: bool = Field(default=False, description="Strict mode: reject on failure")
    max_results: int = Field(default=50, description="Maximum number of results")
    filter_sensitive_info: bool = Field(default=True, description="Filter sensitive information")
    validate_relevance: bool = Field(default=True, description="Validate result relevance")
    sensitive_patterns: List[str] = Field(default_factory=list, description="Sensitive info patterns")


class RAGSettings(BaseModel):
    """RAG system configuration."""
    enabled: bool = Field(default=True, description="Enable RAG system")
    strategy: str = Field(default="multi_round", description="Retrieval strategy: single_round, multi_round, parallel")
    max_rounds: int = Field(default=3, description="Maximum retrieval rounds (for multi_round strategy)")
    query_rewriter: RAGQueryRewriterConfig = Field(default_factory=RAGQueryRewriterConfig)
    sources: List[RAGSourceConfig] = Field(default_factory=list)
    cache: Optional[RAGCacheConfig] = Field(default=None, description="Cache configuration")
    processor: RAGProcessorConfig = Field(default_factory=RAGProcessorConfig, description="Processor configuration")
    input_guardrail: RAGInputGuardrailConfig = Field(default_factory=RAGInputGuardrailConfig, description="Input guardrail configuration")
    output_guardrail: RAGOutputGuardrailConfig = Field(default_factory=RAGOutputGuardrailConfig, description="Output guardrail configuration")
    fallback_on_error: bool = Field(default=True, description="Return empty results on error instead of raising")


class Settings(BaseModel):
    """Application settings."""
    llm: LLMSettings = Field(default_factory=LLMSettings)
    rag: RAGSettings = Field(default_factory=RAGSettings)
    config_path: str = Field(
        default_factory=lambda: str(BACKEND_ROOT / "config" / "app.yaml")
    )
    
    @classmethod
    def from_yaml(cls, config_path: Optional[str] = None) -> Settings:
        """
        Load settings from YAML file.
        
        Args:
            config_path: Path to config file. If None, uses default.
            
        Returns:
            Settings instance
        """
        if config_path is None:
            config_path = os.getenv(
                "TRAVEL_AGENT_CONFIG",
                str(BACKEND_ROOT / "config" / "app.yaml")
            )
        
        config_file = Path(config_path)
        if not config_file.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_path}")
        
        with open(config_file, "r", encoding="utf-8") as f:
            config_data = yaml.safe_load(f) or {}
        
        # Build settings from config data
        llm_data = config_data.get("llm", {})
        llm_settings = LLMSettings(
            provider=llm_data.get("provider", "qwen"),
            model=llm_data.get("model", "qwen-max"),
            timeout=float(llm_data.get("timeout", 30.0)),
            system_prompt_template=llm_data.get("system_prompt_template", ""),
            openai_model=llm_data.get("openai_model")
        )
        
        # Build RAG settings
        rag_data = config_data.get("rag", {})
        rag_query_rewriter_data = rag_data.get("query_rewriter", {})
        rag_query_rewriter = RAGQueryRewriterConfig(
            enabled=rag_query_rewriter_data.get("enabled", True),
            model=rag_query_rewriter_data.get("model")
        )
        
        rag_sources_data = rag_data.get("sources", [])
        rag_sources = [
            RAGSourceConfig(
                type=src.get("type", "retrieval_service"),
                enabled=src.get("enabled", True),
                url=src.get("url"),
                pipeline_name=src.get("pipeline_name", "default"),
                config=src.get("config", {}),
                timeout=src.get("timeout", 60.0)
            )
            for src in rag_sources_data
        ]
        
        # If no RAG sources configured, add default
        if not rag_sources:
            rag_sources.append(RAGSourceConfig(
                type="retrieval_service",
                enabled=True,
                url="http://localhost:8003",
                pipeline_name="default",
                timeout=60.0
            ))
        
        # Parse cache config
        rag_cache_data = rag_data.get("cache", {})
        rag_cache = None
        if rag_cache_data.get("enabled", True):
            rag_cache = RAGCacheConfig(
                enabled=rag_cache_data.get("enabled", True),
                ttl_seconds=rag_cache_data.get("ttl_seconds", 300),
                max_size=rag_cache_data.get("max_size", 1000)
            )
        
        # Parse processor config
        rag_processor_data = rag_data.get("processor", {})
        rag_processor = RAGProcessorConfig(
            ranking_strategy=rag_processor_data.get("ranking_strategy", "score"),
            merge_keep_best_score=rag_processor_data.get("merge_keep_best_score", True)
        )
        
        # Parse input guardrail config
        rag_input_guardrail_data = rag_data.get("input_guardrail", {})
        rag_input_guardrail = RAGInputGuardrailConfig(
            enabled=rag_input_guardrail_data.get("enabled", True),
            strict_mode=rag_input_guardrail_data.get("strict_mode", False),
            max_query_length=rag_input_guardrail_data.get("max_query_length", 1000),
            blocked_patterns=rag_input_guardrail_data.get("blocked_patterns", []),
            sensitive_patterns=rag_input_guardrail_data.get("sensitive_patterns", [])
        )
        
        # Parse output guardrail config
        rag_output_guardrail_data = rag_data.get("output_guardrail", {})
        rag_output_guardrail = RAGOutputGuardrailConfig(
            enabled=rag_output_guardrail_data.get("enabled", True),
            strict_mode=rag_output_guardrail_data.get("strict_mode", False),
            max_results=rag_output_guardrail_data.get("max_results", 50),
            filter_sensitive_info=rag_output_guardrail_data.get("filter_sensitive_info", True),
            validate_relevance=rag_output_guardrail_data.get("validate_relevance", True),
            sensitive_patterns=rag_output_guardrail_data.get("sensitive_patterns", [])
        )
        
        rag_settings = RAGSettings(
            enabled=rag_data.get("enabled", True),
            strategy=rag_data.get("strategy", "multi_round"),
            max_rounds=rag_data.get("max_rounds", 3),
            query_rewriter=rag_query_rewriter,
            sources=rag_sources,
            cache=rag_cache,
            processor=rag_processor,
            input_guardrail=rag_input_guardrail,
            output_guardrail=rag_output_guardrail,
            fallback_on_error=rag_data.get("fallback_on_error", True)
        )
        
        return cls(
            llm=llm_settings,
            rag=rag_settings,
            config_path=str(config_path)
        )
    
    def save_to_yaml(self, config_path: Optional[str] = None) -> None:
        """
        Save settings to YAML file.
        
        Args:
            config_path: Path to config file. If None, uses current config_path.
        """
        if config_path is None:
            config_path = self.config_path
        
        config_file = Path(config_path)
        
        # Load existing config to preserve other settings
        existing_config: Dict[str, Any] = {}
        if config_file.exists():
            with open(config_file, "r", encoding="utf-8") as f:
                existing_config = yaml.safe_load(f) or {}
        
        # Update LLM settings
        if "llm" not in existing_config:
            existing_config["llm"] = {}
        existing_config["llm"]["provider"] = self.llm.provider
        existing_config["llm"]["model"] = self.llm.model
        existing_config["llm"]["timeout"] = self.llm.timeout
        existing_config["llm"]["system_prompt_template"] = self.llm.system_prompt_template
        if self.llm.openai_model:
            existing_config["llm"]["openai_model"] = self.llm.openai_model
        # Preserve openai_base_url if exists
        if "openai_base_url" in existing_config.get("llm", {}):
            existing_config["llm"]["openai_base_url"] = existing_config["llm"]["openai_base_url"]
        
        # Write to file
        with open(config_file, "w", encoding="utf-8") as f:
            yaml.dump(existing_config, f, allow_unicode=True, default_flow_style=False, sort_keys=False)
        
        # Update config_path
        self.config_path = str(config_path)
    
    def save_llm_config(self, provider: str, model: str) -> None:
        """Save LLM provider and model configuration."""
        self.llm.provider = provider
        if provider == "openai":
            # Update openai_model in config
            self.llm.openai_model = model
        else:
            self.llm.model = model
        self.save_to_yaml()
    
    def save_system_prompt_template(self, template: str) -> None:
        """Save system prompt template."""
        self.llm.system_prompt_template = template
        self.save_to_yaml()



# Global settings instance
_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """Get global settings instance."""
    global _settings
    if _settings is None:
        _settings = Settings.from_yaml()
    return _settings


def reload_settings(config_path: Optional[str] = None) -> Settings:
    """Reload settings from file."""
    global _settings
    _settings = Settings.from_yaml(config_path)
    return _settings
