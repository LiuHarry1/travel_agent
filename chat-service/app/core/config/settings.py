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


class RAGSettings(BaseModel):
    """RAG system configuration."""
    enabled: bool = Field(default=True, description="Enable RAG system")
    strategy: str = Field(default="multi_round", description="Retrieval strategy: single_round, multi_round, parallel")
    max_rounds: int = Field(default=3, description="Maximum retrieval rounds (for multi_round strategy)")
    query_rewriter: RAGQueryRewriterConfig = Field(default_factory=RAGQueryRewriterConfig)
    sources: List[RAGSourceConfig] = Field(default_factory=list)


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
                config=src.get("config", {})
            )
            for src in rag_sources_data
        ]
        
        # If no RAG sources configured, add default
        if not rag_sources:
            rag_sources.append(RAGSourceConfig(
                type="retrieval_service",
                enabled=True,
                url="http://localhost:8001",
                pipeline_name="default"
            ))
        
        rag_settings = RAGSettings(
            enabled=rag_data.get("enabled", True),
            strategy=rag_data.get("strategy", "multi_round"),
            max_rounds=rag_data.get("max_rounds", 3),
            query_rewriter=rag_query_rewriter,
            sources=rag_sources
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
