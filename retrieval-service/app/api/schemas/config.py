"""Configuration API schemas."""
from pydantic import BaseModel
from typing import Dict, Any, Optional


class PipelineListResponse(BaseModel):
    """Response model for pipeline list."""
    default: Optional[str] = None
    pipelines: list[str]


class PipelineConfigRequest(BaseModel):
    """Request model for pipeline configuration."""
    pipeline_name: str
    yaml: str


class PipelineConfigResponse(BaseModel):
    """Response model for pipeline configuration."""
    pipeline_name: str
    yaml: str


class ValidationResponse(BaseModel):
    """Response model for configuration validation."""
    valid: bool
    errors: Dict[str, Any] = {}


class DefaultPipelineRequest(BaseModel):
    """Request model for setting default pipeline."""
    pipeline_name: str


class UpdatePipelineRequest(BaseModel):
    """Request model for updating pipeline configuration."""
    yaml: str


class ValidatePipelineRequest(BaseModel):
    """Request model for validating pipeline configuration."""
    yaml: Optional[str] = None

