"""Project-level configuration management with YAML storage and env substitution."""
from __future__ import annotations

import os
import threading
import time
from pathlib import Path
from typing import Any, Dict, Optional

import yaml
from pydantic import BaseModel, Field, ValidationError, root_validator

# YAML file path (relative to repo root)
DEFAULT_CONFIG_PATH = Path(__file__).resolve().parent.parent / "projects.yaml"

# Regex patterns for environment variable substitution
ENV_PREFIX = "env:"


class MilvusConfig(BaseModel):
    """Milvus connection configuration."""

    host: str = "localhost"
    port: int = 19530
    user: str = ""
    password: str = ""
    database: str = "default"
    collection: str = "knowledge_base"


class RerankConfig(BaseModel):
    """Rerank service configuration."""

    api_url: str
    model: str = ""
    timeout: int = 30


class LLMFilterConfig(BaseModel):
    """LLM filter configuration."""

    api_key: str = ""
    base_url: str
    model: str


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


class ProjectConfig(BaseModel):
    """Single project configuration."""

    milvus: MilvusConfig
    embedding_models: list[str] = Field(default_factory=list)
    rerank: RerankConfig
    llm_filter: LLMFilterConfig
    retrieval: RetrievalParams = RetrievalParams()
    chunk_sizes: ChunkSizes = ChunkSizes()

    class Config:
        extra = "ignore"

    @root_validator(pre=True)
    def _ensure_defaults(cls, values: Dict[str, Any]) -> Dict[str, Any]:
        """Populate optional nested defaults."""
        values.setdefault("retrieval", {})
        values.setdefault("chunk_sizes", {})
        return values


class ProjectsFile(BaseModel):
    """Top-level projects YAML structure."""

    default: str
    projects: Dict[str, ProjectConfig] = Field(default_factory=dict)

    class Config:
        extra = "ignore"


class ProjectConfigManager:
    """Manage project configurations stored in YAML."""

    def __init__(self, path: Optional[Path] = None) -> None:
        self.path = Path(path) if path else DEFAULT_CONFIG_PATH
        self._lock = threading.Lock()
        self._cache: Optional[ProjectsFile] = None
        self._last_mtime: Optional[float] = None
        self.path.parent.mkdir(parents=True, exist_ok=True)

    # Public API -----------------------------------------------------------------
    def get_projects(self) -> ProjectsFile:
        """Get all project configurations (auto-reload on change)."""
        self._ensure_loaded()
        assert self._cache is not None
        return self._cache

    def get_project(self, project_name: Optional[str] = None) -> ProjectConfig:
        """Get a single project configuration by name (falls back to default)."""
        projects_file = self.get_projects()
        name = project_name or projects_file.default
        if name not in projects_file.projects:
            raise KeyError(f"Project '{name}' not found in configuration")
        return projects_file.projects[name]

    def set_project(self, project_name: str, config: Dict[str, Any]) -> ProjectsFile:
        """Create or update a project configuration and persist to YAML."""
        with self._lock:
            projects_file = self._load_projects(force_reload=True)
            validated = ProjectConfig.parse_obj(self._resolve_env(config))
            projects_file.projects[project_name] = validated
            if not projects_file.default:
                projects_file.default = project_name
            self._write_projects(projects_file)
            self._cache = projects_file
            return projects_file

    def delete_project(self, project_name: str) -> ProjectsFile:
        """Delete a project configuration."""
        with self._lock:
            projects_file = self._load_projects(force_reload=True)
            if project_name not in projects_file.projects:
                raise KeyError(f"Project '{project_name}' not found")
            del projects_file.projects[project_name]
            if projects_file.default == project_name:
                projects_file.default = next(iter(projects_file.projects), "")
            self._write_projects(projects_file)
            self._cache = projects_file
            return projects_file

    def set_default(self, project_name: str) -> ProjectsFile:
        """Set the default project name."""
        with self._lock:
            projects_file = self._load_projects(force_reload=True)
            if project_name not in projects_file.projects:
                raise KeyError(f"Project '{project_name}' not found")
            projects_file.default = project_name
            self._write_projects(projects_file)
            self._cache = projects_file
            return projects_file

    def refresh(self) -> ProjectsFile:
        """Force reload configuration from disk."""
        with self._lock:
            self._cache = None
            return self._load_projects(force_reload=True)

    # Internal helpers -----------------------------------------------------------
    def _ensure_loaded(self) -> None:
        """Load from disk if not loaded or if file changed."""
        with self._lock:
            current_mtime = self._get_mtime()
            if self._cache is None or (
                current_mtime is not None and self._last_mtime != current_mtime
            ):
                self._load_projects(force_reload=True)

    def _get_mtime(self) -> Optional[float]:
        try:
            return self.path.stat().st_mtime
        except FileNotFoundError:
            return None

    def _load_projects(self, force_reload: bool = False) -> ProjectsFile:
        """Load and validate projects YAML."""
        if self._cache is not None and not force_reload:
            return self._cache

        raw_data = self._read_yaml()
        normalized = self._resolve_env(raw_data or {})
        try:
            projects_file = ProjectsFile.parse_obj(normalized)
        except ValidationError as exc:
            raise ValueError(f"Invalid projects configuration: {exc}") from exc

        self._cache = projects_file
        self._last_mtime = self._get_mtime()
        return projects_file

    def _read_yaml(self) -> Dict[str, Any]:
        """Read YAML file safely with shared lock."""
        if not self.path.exists():
            return {}

        with self._file_lock(shared=True):
            with self.path.open("r", encoding="utf-8") as f:
                return yaml.safe_load(f) or {}

    def _write_projects(self, projects_file: ProjectsFile) -> None:
        """Write projects YAML with exclusive lock."""
        data = projects_file.dict()
        with self._file_lock(shared=False):
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

    # File lock helper -----------------------------------------------------------
    def _file_lock(self, shared: bool):
        """Context manager for file-level locking."""
        return _FileLock(self.path, shared=shared)


class _FileLock:
    """Simple file lock using fcntl (POSIX)."""

    def __init__(self, path: Path, shared: bool) -> None:
        self.path = path
        self.shared = shared
        self.file = None

    def __enter__(self):
        import fcntl  # Local import; available on POSIX

        # Ensure file exists
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.file = self.path.open("a+", encoding="utf-8")
        lock_type = fcntl.LOCK_SH if self.shared else fcntl.LOCK_EX
        fcntl.flock(self.file.fileno(), lock_type)
        # Move cursor to start for readers
        if self.shared:
            self.file.seek(0)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        import fcntl

        if self.file:
            fcntl.flock(self.file.fileno(), fcntl.LOCK_UN)
            self.file.close()
        return False


# Convenience singleton
project_config_manager = ProjectConfigManager()

