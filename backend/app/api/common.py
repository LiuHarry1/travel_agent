"""Common API routes (health check, configuration)."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from ..config import get_config, reload_config
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
    config = get_config()
    result = {
        "system_prompt_template": config.system_prompt_template,
    }
    # Include checklist for backward compatibility if it exists in config
    try:
        checklist_data = config._config.get("default_checklist", [])
        if checklist_data:
            result["checklist"] = [
                {"id": item.get("id", ""), "description": item.get("description", "")}
                for item in checklist_data
            ]
    except (AttributeError, ValueError, KeyError):
        # Checklist not available or not configured
        pass
    return result


@router.post("/config")
def save_config(request: ConfigUpdateRequest) -> dict:
    """Save system prompt template configuration."""
    try:
        config = get_config()
        
        # If checklist is provided, use the old method for backward compatibility
        if request.checklist is not None:
            config.save_config(request.system_prompt_template, request.checklist)
        else:
            # Use the new method that only saves system_prompt_template
            config.save_system_prompt_template(request.system_prompt_template)
        
        reload_config()
        return {"status": "success", "message": "Configuration saved successfully"}
    except Exception as exc:
        error_msg = format_error_message(exc, "Failed to save configuration")
        raise HTTPException(status_code=500, detail=error_msg) from exc

