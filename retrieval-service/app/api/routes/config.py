"""Configuration management API routes."""
from fastapi import APIRouter, HTTPException
from typing import Dict, Any, Optional
import yaml
from app.api.schemas.config import (
    PipelineListResponse,
    PipelineConfigRequest,
    PipelineConfigResponse,
    ValidationResponse,
    DefaultPipelineRequest,
    UpdatePipelineRequest,
    ValidatePipelineRequest
)
from app.infrastructure.config.pipeline_config import pipeline_config_manager, PipelineConfig
from app.infrastructure.config.config_validator import config_validator
from app.services.service_factory import clear_cache
from app.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter()


@router.get("/pipelines", response_model=PipelineListResponse)
async def get_pipelines():
    """Get all pipeline names and default pipeline."""
    try:
        pipelines_file = pipeline_config_manager.get_pipelines()
        return {
            "default": pipelines_file.default,
            "pipelines": list(pipelines_file.pipelines.keys())
        }
    except Exception as e:
        logger.error(f"Failed to get pipelines: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/pipelines/{pipeline_name}", response_model=PipelineConfigResponse)
async def get_pipeline(pipeline_name: str):
    """Get pipeline configuration in YAML format."""
    try:
        pipeline_config = pipeline_config_manager.get_pipeline(pipeline_name)
        # Convert to dict and then to YAML, excluding None values
        config_dict = pipeline_config.dict(exclude_none=True)
        # Also remove None values from nested dicts
        config_dict = {k: v for k, v in config_dict.items() if v is not None}
        yaml_str = yaml.safe_dump(config_dict, sort_keys=False, allow_unicode=True)
        return {
            "pipeline_name": pipeline_name,
            "yaml": yaml_str
        }
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Pipeline '{pipeline_name}' not found")
    except Exception as e:
        logger.error(f"Failed to get pipeline: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/pipelines", response_model=PipelineConfigResponse)
async def create_pipeline(request: PipelineConfigRequest):
    """Create a new pipeline configuration."""
    try:
        # Parse YAML
        try:
            config_dict = yaml.safe_load(request.yaml)
            if not isinstance(config_dict, dict):
                raise ValueError("Configuration must be a YAML object")
        except yaml.YAMLError as e:
            raise HTTPException(status_code=400, detail=f"Invalid YAML format: {e}")
        
        # Validate configuration
        try:
            pipeline_config_manager.set_pipeline(request.pipeline_name, config_dict)
        except Exception as e:
            logger.error(f"Failed to create pipeline: {e}", exc_info=True)
            raise HTTPException(status_code=400, detail=f"Invalid configuration: {e}")
        
        # Clear cache for this pipeline
        clear_cache(request.pipeline_name)
        
        # Return created configuration
        pipeline_config = pipeline_config_manager.get_pipeline(request.pipeline_name)
        config_dict = pipeline_config.dict(exclude_none=True)
        # Also remove None values from nested dicts
        config_dict = {k: v for k, v in config_dict.items() if v is not None}
        yaml_str = yaml.safe_dump(config_dict, sort_keys=False, allow_unicode=True)
        
        logger.info(f"Created pipeline: {request.pipeline_name}")
        return {
            "pipeline_name": request.pipeline_name,
            "yaml": yaml_str
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create pipeline: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/pipelines/{pipeline_name}", response_model=PipelineConfigResponse)
async def update_pipeline(pipeline_name: str, request: UpdatePipelineRequest):
    """Update pipeline configuration."""
    try:
        # Check if pipeline exists
        try:
            pipeline_config_manager.get_pipeline(pipeline_name)
        except KeyError:
            raise HTTPException(status_code=404, detail=f"Pipeline '{pipeline_name}' not found")
        
        # Parse YAML
        try:
            config_dict = yaml.safe_load(request.yaml)
            if not isinstance(config_dict, dict):
                raise ValueError("Configuration must be a YAML object")
        except yaml.YAMLError as e:
            raise HTTPException(status_code=400, detail=f"Invalid YAML format: {e}")
        
        # Update configuration
        try:
            pipeline_config_manager.set_pipeline(pipeline_name, config_dict)
        except Exception as e:
            logger.error(f"Failed to update pipeline: {e}", exc_info=True)
            raise HTTPException(status_code=400, detail=f"Invalid configuration: {e}")
        
        # Clear cache for this pipeline
        clear_cache(pipeline_name)
        
        # Return updated configuration
        pipeline_config = pipeline_config_manager.get_pipeline(pipeline_name)
        config_dict = pipeline_config.dict(exclude_none=True)
        # Also remove None values from nested dicts
        config_dict = {k: v for k, v in config_dict.items() if v is not None}
        yaml_str = yaml.safe_dump(config_dict, sort_keys=False, allow_unicode=True)
        
        logger.info(f"Updated pipeline: {pipeline_name}")
        return {
            "pipeline_name": pipeline_name,
            "yaml": yaml_str
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update pipeline: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/pipelines/{pipeline_name}")
async def delete_pipeline(pipeline_name: str):
    """Delete a pipeline configuration."""
    try:
        # Check if pipeline exists
        try:
            pipeline_config_manager.get_pipeline(pipeline_name)
        except KeyError:
            raise HTTPException(status_code=404, detail=f"Pipeline '{pipeline_name}' not found")
        
        # Delete pipeline
        pipeline_config_manager.delete_pipeline(pipeline_name)
        
        # Clear cache for this pipeline
        clear_cache(pipeline_name)
        
        logger.info(f"Deleted pipeline: {pipeline_name}")
        return {"message": f"Pipeline '{pipeline_name}' deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete pipeline: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/pipelines/{pipeline_name}/validate", response_model=ValidationResponse)
async def validate_pipeline(pipeline_name: str, request: Optional[ValidatePipelineRequest] = None):
    """Validate pipeline configuration."""
    try:
        # If YAML is provided in request, validate it
        if request and request.yaml:
            try:
                config_dict = yaml.safe_load(request.yaml)
                if not isinstance(config_dict, dict):
                    return ValidationResponse(valid=False, errors={"yaml": "Configuration must be a YAML object"})
                
                # Try to create a temporary pipeline config
                try:
                    temp_config = PipelineConfig.parse_obj(config_dict)
                    validation_result = config_validator.validate_project(temp_config)
                    return ValidationResponse(
                        valid=validation_result.ok,
                        errors=validation_result.details
                    )
                except Exception as e:
                    return ValidationResponse(valid=False, errors={"validation": str(e)})
            except yaml.YAMLError as e:
                return ValidationResponse(valid=False, errors={"yaml": f"Invalid YAML format: {e}"})
        
        # Otherwise validate existing pipeline
        try:
            pipeline_config = pipeline_config_manager.get_pipeline(pipeline_name)
            validation_result = config_validator.validate_project(pipeline_config)
            return ValidationResponse(
                valid=validation_result.ok,
                errors=validation_result.details
            )
        except KeyError:
            raise HTTPException(status_code=404, detail=f"Pipeline '{pipeline_name}' not found")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to validate pipeline: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/default", response_model=Dict[str, str])
async def set_default_pipeline(request: DefaultPipelineRequest):
    """Set default pipeline."""
    try:
        pipeline_config_manager.set_default(request.pipeline_name)
        logger.info(f"Set default pipeline: {request.pipeline_name}")
        return {"default": request.pipeline_name}
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Pipeline '{request.pipeline_name}' not found")
    except Exception as e:
        logger.error(f"Failed to set default pipeline: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

