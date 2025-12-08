"""Pipeline-level configuration management with YAML storage and env substitution."""
from __future__ import annotations

import os
import threading
import time
from pathlib import Path
from typing import Any, Dict, Optional, List

import yaml
from pydantic import BaseModel, Field, ValidationError, root_validator

# YAML file path (relative to repo root)
DEFAULT_CONFIG_PATH = Path(__file__).resolve().parent.parent.parent / "pipelines.yaml"

# Regex patterns for environment variable substitution
ENV_PREFIX = "env:"


class MilvusConfig(BaseModel):
    """Milvus connection configuration."""

    host: str = "localhost"
    port: int = 19530
    user: str = ""
    password: str = ""
    database: str = "default"
    collection: str = "memory_doc_db"


class RerankConfig(BaseModel):
    """Rerank service configuration."""

    api_url: str = ""
    model: str = ""
    timeout: int = 30


class LLMFilterConfig(BaseModel):
    """LLM filter configuration."""

    api_key: str = ""
    base_url: str = ""
    model: str = ""


class RetrievalParams(BaseModel):
    """Retrieval pipeline parameters."""

    top_k_per_model: int = 10
    rerank_top_k: int = 20
    final_top_k: int = 10


class ChunkSizes(BaseModel):
    """Chunk sizing for each stage."""

    initial_search: int = 100
    rerank_input: int = 50
    llm_filter_input: int = 20


class EmbeddingModelConfig(BaseModel):
    """Embedding model configuration with optional collection override."""
    model: str  # e.g., "qwen" or "qwen:text-embedding-v2"
    collection: Optional[str] = None  # If None, uses default collection from milvus config

    @classmethod
    def from_string(cls, value: str, default_collection: str) -> "EmbeddingModelConfig":
        """Parse from string format: 'model' or 'model:collection' or 'provider:model' or 'provider:model:collection'"""
        parts = value.split(":")
        if len(parts) == 1:
            # Just model name
            return cls(model=parts[0], collection=default_collection)
        elif len(parts) == 2:
            # Could be "provider:model" or "model:collection"
            # Try to determine: if first part is a known provider, treat as provider:model
            known_providers = ["qwen", "bge", "openai"]
            if parts[0] in known_providers:
                return cls(model=value, collection=default_collection)
            else:
                # Treat as model:collection
                return cls(model=parts[0], collection=parts[1])
        elif len(parts) == 3:
            # provider:model:collection
            return cls(model=f"{parts[0]}:{parts[1]}", collection=parts[2])
        else:
            # Fallback: use entire string as model
            return cls(model=value, collection=default_collection)


class PipelineConfig(BaseModel):
    """Single pipeline configuration."""

    milvus: MilvusConfig
    embedding_models: List[Any] = Field(default_factory=lambda: ["qwen"])  # Can be string or EmbeddingModelConfig dict
    rerank: Optional[RerankConfig] = None
    llm_filter: Optional[LLMFilterConfig] = None
    retrieval: RetrievalParams = RetrievalParams()
    chunk_sizes: ChunkSizes = ChunkSizes()

    class Config:
        extra = "ignore"

    @root_validator(pre=True)
    def _ensure_defaults(cls, values: Dict[str, Any]) -> Dict[str, Any]:
        """Populate optional nested defaults."""
        values.setdefault("retrieval", {})
        values.setdefault("chunk_sizes", {})
        # Don't convert embedding_models here - keep as-is for Pydantic to handle
        # rerank and llm_filter are optional - only include if provided and not empty
        # If rerank is provided but api_url is empty, treat as None
        if "rerank" in values:
            rerank = values.get("rerank", {})
            if isinstance(rerank, dict) and (not rerank.get("api_url") or not rerank.get("api_url", "").strip()):
                values.pop("rerank", None)
        # If llm_filter is provided but base_url and model are empty, treat as None
        if "llm_filter" in values:
            llm_filter = values.get("llm_filter", {})
            if isinstance(llm_filter, dict):
                base_url = llm_filter.get("base_url", "")
                model = llm_filter.get("model", "")
                if (not base_url or not base_url.strip()) and (not model or not model.strip()):
                    values.pop("llm_filter", None)
        return values
    
    def get_embedding_model_configs(self) -> List[EmbeddingModelConfig]:
        """Get normalized embedding model configurations."""
        configs = []
        default_collection = self.milvus.collection
        for model in self.embedding_models:
            if isinstance(model, EmbeddingModelConfig):
                # Ensure collection is set if None
                if model.collection is None:
                    model.collection = default_collection
                configs.append(model)
            elif isinstance(model, str):
                configs.append(EmbeddingModelConfig.from_string(model, default_collection))
            elif isinstance(model, dict):
                # If collection not specified, use default
                if "collection" not in model:
                    model["collection"] = default_collection
                configs.append(EmbeddingModelConfig(**model))
            else:
                # Fallback: convert to string and parse
                configs.append(EmbeddingModelConfig.from_string(str(model), default_collection))
        return configs


class PipelinesFile(BaseModel):
    """Top-level pipelines YAML structure."""

    default: Optional[str] = None
    pipelines: Dict[str, PipelineConfig] = Field(default_factory=dict)

    class Config:
        extra = "ignore"


class PipelineConfigManager:
    """Manage pipeline configurations stored in YAML."""

    def __init__(self, path: Optional[Path] = None) -> None:
        self.path = Path(path) if path else DEFAULT_CONFIG_PATH
        self._lock = threading.Lock()
        self._cache: Optional[PipelinesFile] = None
        self._last_mtime: Optional[float] = None
        self.path.parent.mkdir(parents=True, exist_ok=True)

    # Public API -----------------------------------------------------------------
    def get_pipelines(self) -> PipelinesFile:
        """Get all pipeline configurations (auto-reload on change)."""
        self._ensure_loaded()
        assert self._cache is not None
        return self._cache

    def get_pipeline(self, pipeline_name: Optional[str] = None) -> PipelineConfig:
        """Get a single pipeline configuration by name (falls back to default)."""
        pipelines_file = self.get_pipelines()
        name = pipeline_name or pipelines_file.default
        if not name:
            raise KeyError("No default pipeline set and no pipeline name provided")
        if name not in pipelines_file.pipelines:
            raise KeyError(f"Pipeline '{name}' not found in configuration")
        return pipelines_file.pipelines[name]

    def set_pipeline(self, pipeline_name: str, config: Dict[str, Any]) -> PipelinesFile:
        """Create or update a pipeline configuration and persist to YAML."""
        with self._lock:
            pipelines_file = self._load_pipelines(force_reload=True)
            validated = PipelineConfig.parse_obj(self._resolve_env(config))
            pipelines_file.pipelines[pipeline_name] = validated
            if pipelines_file.default is None:
                pipelines_file.default = pipeline_name
            self._write_pipelines(pipelines_file)
            self._cache = pipelines_file
            return pipelines_file

    def delete_pipeline(self, pipeline_name: str) -> PipelinesFile:
        """Delete a pipeline configuration."""
        with self._lock:
            pipelines_file = self._load_pipelines(force_reload=True)
            if pipeline_name not in pipelines_file.pipelines:
                raise KeyError(f"Pipeline '{pipeline_name}' not found")
            del pipelines_file.pipelines[pipeline_name]
            if pipelines_file.default == pipeline_name:
                pipelines_file.default = next(iter(pipelines_file.pipelines), None)
            self._write_pipelines(pipelines_file)
            self._cache = pipelines_file
            return pipelines_file

    def set_default(self, pipeline_name: str) -> PipelinesFile:
        """Set the default pipeline name."""
        with self._lock:
            pipelines_file = self._load_pipelines(force_reload=True)
            if pipeline_name not in pipelines_file.pipelines:
                raise KeyError(f"Pipeline '{pipeline_name}' not found")
            pipelines_file.default = pipeline_name
            self._write_pipelines(pipelines_file)
            self._cache = pipelines_file
            return pipelines_file

    def refresh(self) -> PipelinesFile:
        """Force reload configuration from disk."""
        with self._lock:
            self._cache = None
            return self._load_pipelines(force_reload=True)

    # Internal helpers -----------------------------------------------------------
    def _ensure_loaded(self) -> None:
        """Load from disk if not loaded or if file changed."""
        with self._lock:
            current_mtime = self._get_mtime()
            if self._cache is None or (
                current_mtime is not None and self._last_mtime != current_mtime
            ):
                self._load_pipelines(force_reload=True)

    def _get_mtime(self) -> Optional[float]:
        try:
            return self.path.stat().st_mtime
        except FileNotFoundError:
            return None

    def _load_pipelines(self, force_reload: bool = False) -> PipelinesFile:
        """Load and validate pipelines YAML."""
        if self._cache is not None and not force_reload:
            return self._cache

        raw_data = self._read_yaml()
        normalized = self._resolve_env(raw_data or {})
        # Ensure default structure for empty files
        if not normalized:
            normalized = {"default": "memory", "pipelines": {}}
        try:
            pipelines_file = PipelinesFile.parse_obj(normalized)
        except ValidationError as exc:
            raise ValueError(f"Invalid pipelines configuration: {exc}") from exc

        # Create default "memory" pipeline if no pipelines exist
        if not pipelines_file.pipelines:
            default_config = self._create_default_memory_pipeline()
            pipelines_file.pipelines["memory"] = default_config
            pipelines_file.default = "memory"
            # Persist the default pipeline to disk
            self._write_pipelines(pipelines_file)
        # Ensure default is set to "memory" if it's None but pipelines exist
        elif pipelines_file.default is None and "memory" in pipelines_file.pipelines:
            pipelines_file.default = "memory"
            self._write_pipelines(pipelines_file)
        # If default is None and memory doesn't exist, set default to first pipeline
        elif pipelines_file.default is None and pipelines_file.pipelines:
            pipelines_file.default = next(iter(pipelines_file.pipelines))
            self._write_pipelines(pipelines_file)

        self._cache = pipelines_file
        self._last_mtime = self._get_mtime()
        return pipelines_file

    def _read_yaml(self) -> Dict[str, Any]:
        """Read YAML file."""
        if not self.path.exists():
            return {}

        with self.path.open("r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}

    def _write_pipelines(self, pipelines_file: PipelinesFile) -> None:
        """Write pipelines YAML."""
        data = pipelines_file.dict(exclude_none=True)
        # Also remove None values from nested pipeline configs
        if "pipelines" in data:
            for pipeline_name, pipeline_data in data["pipelines"].items():
                if isinstance(pipeline_data, dict):
                    # Remove None values from pipeline config
                    data["pipelines"][pipeline_name] = {
                        k: v for k, v in pipeline_data.items() if v is not None
                    }
        with self.path.open("w", encoding="utf-8") as f:
            yaml.safe_dump(data, f, sort_keys=False, allow_unicode=False)
        self._last_mtime = self._get_mtime()

    def _resolve_env(self, obj: Any) -> Any:
        """Recursively replace env placeholders in configuration."""
        if isinstance(obj, dict):
            return {k: self._resolve_env(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return [self._resolve_env(item) for item in obj]
        if isinstance(obj, str):
            return self._resolve_env_string(obj)
        return obj

    def _create_default_memory_pipeline(self) -> PipelineConfig:
        """Create default 'memory' pipeline configuration."""
        default_config_dict = {
            "milvus": {
                "host": "localhost",
                "port": 19530,
                "user": "",
                "password": "",
                "database": "default",
                "collection": "memory_doc_db"
            },
            "embedding_models": ["qwen"],
            # rerank and llm_filter are optional - not included by default
            "retrieval": {
                "top_k_per_model": 10,
                "rerank_top_k": 20,
                "final_top_k": 10
            },
            "chunk_sizes": {
                "initial_search": 100,
                "rerank_input": 50,
                "llm_filter_input": 20
            }
        }
        # Resolve environment variables in the default config
        resolved = self._resolve_env(default_config_dict)
        return PipelineConfig.parse_obj(resolved)

    def _resolve_env_string(self, value: str) -> str:
        """Resolve environment variable references."""
        # Single value: env:VAR_NAME
        if value.startswith(ENV_PREFIX):
            var_name = value[len(ENV_PREFIX) :].strip()
            return os.getenv(var_name, "")

        # Embedded ${VAR_NAME} substitutions
        result = ""
        idx = 0
        while idx < len(value):
            start = value.find("${", idx)
            if start == -1:
                result += value[idx:]
                break
            result += value[idx:start]
            end = value.find("}", start)
            if end == -1:
                # No closing brace; return as-is
                result += value[start:]
                break
            var_name = value[start + 2 : end].strip()
            result += os.getenv(var_name, "")
            idx = end + 1
        return result



# Convenience singleton
pipeline_config_manager = PipelineConfigManager()

