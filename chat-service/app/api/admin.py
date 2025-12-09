"""Admin API routes for managing LLM configuration."""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from ..config import get_config, reload_config
from ..llm.provider import LLMProvider
from ..utils.exceptions import format_error_message

import logging

logger = logging.getLogger(__name__)

router = APIRouter()


class ProviderInfo(BaseModel):
    """Provider information."""
    value: str = Field(..., description="Provider identifier")
    label: str = Field(..., description="Provider display name")


class ProvidersResponse(BaseModel):
    """Response model for available providers."""
    providers: List[ProviderInfo]


class LLMConfigResponse(BaseModel):
    """Response model for LLM configuration."""
    provider: str = Field(..., description="Current LLM provider")
    model: str = Field(..., description="Current model name")
    openai_base_url: Optional[str] = Field(None, description="OpenAI base URL (if provider is openai)")


class LLMConfigUpdateRequest(BaseModel):
    """Request model for updating LLM configuration."""
    provider: str = Field(..., description="LLM provider (qwen, openai)")
    model: str = Field(..., description="Model name")
    openai_base_url: Optional[str] = Field(None, description="OpenAI base URL (optional, for OpenAI provider)")


class ModelsResponse(BaseModel):
    """Response model for available models."""
    provider: str
    models: List[str]


@router.get("/providers", response_model=ProvidersResponse)
def get_providers() -> ProvidersResponse:
    """Get list of available LLM providers."""
    providers = [
        ProviderInfo(value="qwen", label="Qwen (Alibaba DashScope)"),
        ProviderInfo(value="openai", label="OpenAI API"),
    ]
    return ProvidersResponse(providers=providers)


@router.get("/config", response_model=LLMConfigResponse)
def get_llm_config() -> LLMConfigResponse:
    """Get current LLM configuration."""
    try:
        config = get_config()
        provider = config.llm_provider
        
        # Get model based on provider
        if provider == "openai":
            model = config._config.get("llm", {}).get("openai_model", "gpt-4")
        else:
            model = config.llm_model
        
        # Get provider-specific URLs
        openai_base_url = None
        if provider == "openai":
            openai_base_url = os.getenv("OPENAI_BASE_URL") or config._config.get("llm", {}).get("openai_base_url")
        
        return LLMConfigResponse(
            provider=provider, 
            model=model, 
            openai_base_url=openai_base_url
        )
    except Exception as exc:
        error_msg = format_error_message(exc, "Failed to get LLM configuration")
        raise HTTPException(status_code=500, detail=error_msg) from exc


@router.post("/config", response_model=Dict[str, Any])
def update_llm_config(request: LLMConfigUpdateRequest) -> Dict[str, Any]:
    """Update LLM configuration."""
    try:
        # Validate provider
        try:
            LLMProvider(request.provider.lower())
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported provider: {request.provider}. Supported providers: {[p.value for p in LLMProvider]}"
            )
        
        # Update provider-specific URLs
        if request.provider.lower() == "openai" and request.openai_base_url:
            # Update environment variable
            os.environ["OPENAI_BASE_URL"] = request.openai_base_url.rstrip("/")
            # Also update config file
            config = get_config()
            llm_config = config._config.get("llm", {})
            llm_config["openai_base_url"] = request.openai_base_url.rstrip("/")
            config._config["llm"] = llm_config
            config._save_config()
        
        # Save configuration
        config = get_config()
        config.save_llm_config(request.provider.lower(), request.model)
        
        # Reload config to ensure changes take effect
        reload_config()
        
        return {
            "status": "success",
            "message": "LLM configuration updated successfully",
            "provider": request.provider.lower(),
            "model": request.model
        }
    except HTTPException:
        raise
    except Exception as exc:
        error_msg = format_error_message(exc, "Failed to update LLM configuration")
        raise HTTPException(status_code=500, detail=error_msg) from exc


@router.get("/models", response_model=ModelsResponse)
def get_available_models(provider: Optional[str] = None) -> ModelsResponse:
    """Get available models for a provider."""
    try:
        config = get_config()
        
        # Use provided provider or get from config
        if provider is None:
            provider = config.llm_provider
        else:
            # Validate provider
            try:
                LLMProvider(provider.lower())
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail=f"Unsupported provider: {provider}. Supported providers: {[p.value for p in LLMProvider]}"
                )
        
        provider_lower = provider.lower()
        
        if provider_lower == "qwen":
            # Qwen models (common models)
            models = [
                "qwen-plus",
                "qwen-max",
                "qwen-turbo",
                "qwen-max-longcontext",
                "qwen-plus-longcontext"
            ]
            return ModelsResponse(provider=provider_lower, models=models)
        
        elif provider_lower == "openai":
            # OpenAI models (common models)
            models = [
                "gpt-4",
                "gpt-4-turbo",
                "gpt-4-32k",
                "gpt-3.5-turbo",
                "gpt-3.5-turbo-16k",
            ]
            return ModelsResponse(provider=provider_lower, models=models)
        
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Provider {provider_lower} does not support model listing"
            )
    
    except HTTPException:
        raise
    except Exception as exc:
        error_msg = format_error_message(exc, "Failed to get available models")
        raise HTTPException(status_code=500, detail=error_msg) from exc


@router.get("/function-calls", response_model=Dict[str, Any])
def get_function_calls() -> Dict[str, Any]:
    """获取所有可用函数和启用状态"""
    from ..tools import get_function_registry
    registry = get_function_registry()
    
    functions = []
    for func_def in registry.get_all_functions():
        functions.append({
            "name": func_def.name,
            "description": func_def.description,
            "type": func_def.type,
            "schema": func_def.schema,
            "enabled": func_def.enabled,
            "config": func_def.config or {}
        })
    
    return {
        "available_functions": functions,
        "enabled_functions": registry.get_enabled_functions()
    }


@router.post("/function-calls", response_model=Dict[str, Any])
def update_function_calls(request: Dict[str, Any]) -> Dict[str, Any]:
    """更新启用的函数列表和配置"""
    from ..tools import get_function_registry
    registry = get_function_registry()
    
    enabled = request.get("enabled_functions", [])
    configs = request.get("configs", {})
    
    # 先禁用所有函数
    for func_def in registry.get_all_functions():
        registry.disable_function(func_def.name)
    
    # 启用指定的函数
    for name in enabled:
        try:
            registry.enable_function(name)
            # 更新配置
            if name in configs:
                func_def = registry.get_function(name)
                if func_def:
                    if func_def.config is None:
                        func_def.config = {}
                    func_def.config.update(configs[name])
        except ValueError as e:
            logger.warning(f"Failed to enable function {name}: {e}")
    
    # 保存配置
    registry.save_config()
    
    return {
        "status": "success",
        "message": "Function calls updated successfully",
        "enabled_functions": registry.get_enabled_functions()
    }


@router.get("/system-prompt", response_model=Dict[str, Any])
def get_system_prompt() -> Dict[str, Any]:
    """获取系统提示词"""
    try:
        config = get_config()
        return {
            "prompt": config.system_prompt_template,
            "template": config.system_prompt_template
        }
    except Exception as exc:
        error_msg = format_error_message(exc, "Failed to get system prompt")
        raise HTTPException(status_code=500, detail=error_msg) from exc


@router.put("/system-prompt", response_model=Dict[str, Any])
def update_system_prompt(request: Dict[str, str]) -> Dict[str, Any]:
    """更新系统提示词（支持热重载）"""
    try:
        prompt = request.get("prompt") or request.get("template")
        if not prompt:
            raise HTTPException(
                status_code=400,
                detail="'prompt' or 'template' field is required"
            )
        
        config = get_config()
        config.save_system_prompt_template(prompt)
        
        # 重新加载配置
        reload_config()
        
        return {
            "status": "success",
            "message": "System prompt updated successfully",
            "prompt": prompt
        }
    except HTTPException:
        raise
    except Exception as exc:
        error_msg = format_error_message(exc, "Failed to update system prompt")
        raise HTTPException(status_code=500, detail=error_msg) from exc

