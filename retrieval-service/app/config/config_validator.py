"""Configuration validator for project settings."""
from __future__ import annotations

import time
import uuid
from typing import Any, Dict, Tuple

from pydantic import BaseModel

from app.config.project_config import (
    ChunkSizes,
    LLMFilterConfig,
    MilvusConfig,
    ProjectConfig,
    ProjectsFile,
    RerankConfig,
    RetrievalParams,
)

try:
    from pymilvus import connections, utility

    HAS_MILVUS = True
except ImportError:  # pragma: no cover - optional dependency at runtime
    HAS_MILVUS = False

try:
    import requests

    HAS_REQUESTS = True
except ImportError:  # pragma: no cover - optional dependency at runtime
    HAS_REQUESTS = False


class ValidationResult(BaseModel):
    """Validation result with optional details."""

    ok: bool
    details: Dict[str, Any] = {}


class ConfigValidator:
    """Validate project configuration and external connections."""

    def validate_projects(self, projects_file: ProjectsFile) -> ValidationResult:
        """Validate the overall projects file."""
        errors: Dict[str, Any] = {}

        if not projects_file.default:
            errors["default"] = "Default project name is required"
        elif projects_file.default not in projects_file.projects:
            errors["default"] = f"Default project '{projects_file.default}' not found in projects"

        for name, project in projects_file.projects.items():
            result = self.validate_project(project)
            if not result.ok:
                errors[name] = result.details

        return ValidationResult(ok=len(errors) == 0, details=errors)

    def validate_project(self, project: ProjectConfig) -> ValidationResult:
        """Validate a single project configuration."""
        errors: Dict[str, Any] = {}

        if not project.embedding_models:
            errors["embedding_models"] = "At least one embedding model is required"

        # Validate nested configs
        milvus_ok, milvus_err = self._test_milvus(project.milvus)
        if not milvus_ok:
            errors["milvus"] = milvus_err

        rerank_ok, rerank_err = self._test_rerank(project.rerank)
        if not rerank_ok:
            errors["rerank"] = rerank_err

        llm_ok, llm_err = self._test_llm(project.llm_filter)
        if not llm_ok:
            errors["llm_filter"] = llm_err

        # Validate retrieval params
        retrieval_errors = self._validate_retrieval(project.retrieval, project.chunk_sizes)
        if retrieval_errors:
            errors["retrieval"] = retrieval_errors

        return ValidationResult(ok=len(errors) == 0, details=errors)

    # Individual tests -----------------------------------------------------------
    def _test_milvus(self, config: MilvusConfig) -> Tuple[bool, str]:
        """Try connecting to Milvus and check collection existence."""
        if not HAS_MILVUS:
            return False, "pymilvus not installed"

        alias = f"validator-{uuid.uuid4()}"
        try:
            connections.connect(
                alias=alias,
                host=config.host,
                port=config.port,
                user=config.user or None,
                password=config.password or None,
                db_name=getattr(config, "database", None) or None,
            )
            # Check collection existence if utility is available
            if hasattr(utility, "has_collection"):
                exists = utility.has_collection(config.collection, using=alias)
                if not exists:
                    return False, f"Collection '{config.collection}' not found"
            return True, ""
        except Exception as exc:  # pragma: no cover - depends on external service
            return False, str(exc)
        finally:
            try:
                connections.disconnect(alias)
            except Exception:
                pass

    def _test_rerank(self, config: RerankConfig) -> Tuple[bool, str]:
        """Simple health check for rerank service."""
        if not config.api_url:
            return False, "rerank.api_url is required"
        if not HAS_REQUESTS:
            return False, "requests not installed"

        try:
            resp = requests.get(config.api_url, timeout=config.timeout or 10)
            if resp.status_code >= 500:
                return False, f"Rerank service error: {resp.status_code}"
            return True, ""
        except Exception as exc:  # pragma: no cover - external service
            return False, str(exc)

    def _test_llm(self, config: LLMFilterConfig) -> Tuple[bool, str]:
        """Check LLM filter configuration (lightweight)."""
        if not config.base_url:
            return False, "llm_filter.base_url is required"
        # If API key is empty, warn but allow (may rely on env)
        if not config.api_key:
            return True, "LLM API key is empty; ensure environment provides it"
        return True, ""

    def _validate_retrieval(
        self, retrieval: RetrievalParams, chunk_sizes: ChunkSizes
    ) -> Dict[str, str]:
        """Validate retrieval and chunk size parameters."""
        errors: Dict[str, str] = {}
        if retrieval.top_k_per_model <= 0:
            errors["top_k_per_model"] = "must be > 0"
        if retrieval.rerank_top_k <= 0:
            errors["rerank_top_k"] = "must be > 0"
        if retrieval.final_top_k <= 0:
            errors["final_top_k"] = "must be > 0"
        if chunk_sizes.initial_search <= 0:
            errors["chunk_sizes.initial_search"] = "must be > 0"
        if chunk_sizes.rerank_input <= 0:
            errors["chunk_sizes.rerank_input"] = "must be > 0"
        if chunk_sizes.llm_filter_input <= 0:
            errors["chunk_sizes.llm_filter_input"] = "must be > 0"
        return errors


# Convenience singleton
config_validator = ConfigValidator()

