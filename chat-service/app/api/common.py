"""Common API routes (health check, configuration)."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from ..core.config_service import get_config_service
from ..models import ConfigUpdateRequest
from ..utils.exceptions import format_error_message

router = APIRouter()


@router.get("/health")
def health_check() -> dict:
    """Health check endpoint."""
    return {"status": "ok"}


@router.get("/config")
def get_default_config() -> dict:
    """Get default configuration including system prompt template."""
    config_service = get_config_service()
    result = {
        "system_prompt_template": config_service.system_prompt_template,
    }
    # Include checklist for backward compatibility if it exists in config
    try:
        settings = config_service.get_settings()
        if settings.default_checklist:
            result["checklist"] = [
                {"id": item.id, "description": item.description}
                for item in settings.default_checklist
            ]
    except (AttributeError, ValueError, KeyError):
        # Checklist not available or not configured
        pass
    return result


@router.post("/config")
def save_config(request: ConfigUpdateRequest) -> dict:
    """Save system prompt template configuration."""
    try:
        config_service = get_config_service()
        
        # If checklist is provided, use the old method for backward compatibility
        if request.checklist is not None:
            # request.checklist is already List[ChecklistItem] from Pydantic
            config_service.save_config(request.system_prompt_template, request.checklist)
        else:
            # Use the simple method that only saves system_prompt_template
            config_service.save_system_prompt_template(request.system_prompt_template)
        return {"status": "success", "message": "Configuration saved successfully"}
    except Exception as exc:
        error_msg = format_error_message(exc, "Failed to save configuration")
        raise HTTPException(status_code=500, detail=error_msg) from exc

