"""Configuration service for unified configuration management."""
from __future__ import annotations

import logging
from typing import Optional

from ..shared.config import Settings, get_settings, reload_settings

logger = logging.getLogger(__name__)


class ConfigurationService:
    """Unified configuration service with caching and reload support."""
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize configuration service.
        
        Args:
            config_path: Optional path to config file. If None, uses default.
        """
        self._config_path = config_path
        self._settings: Optional[Settings] = None
        self._cache: dict = {}
    
    def get_settings(self) -> Settings:
        """
        Get settings instance (with caching).
        
        Returns:
            Settings instance
        """
        if self._settings is None:
            self._settings = get_settings() if self._config_path is None else Settings.from_yaml(self._config_path)
            logger.debug("Configuration loaded")
        return self._settings
    
    def reload(self) -> None:
        """
        Reload configuration from file and clear cache.
        
        This should be called when configuration changes.
        """
        if self._config_path is None:
            self._settings = reload_settings()
        else:
            self._settings = Settings.from_yaml(self._config_path)
        self._cache.clear()
        logger.info("Configuration reloaded")
    
    def get_llm_config(self) -> dict:
        """Get LLM configuration as dict."""
        settings = self.get_settings()
        return {
            "provider": settings.llm.provider,
            "model": settings.llm.model,
            "timeout": settings.llm.timeout,
            "system_prompt_template": settings.llm.system_prompt_template,
            "openai_model": settings.llm.openai_model,
        }
    
    def get_rag_config(self) -> dict:
        """Get RAG configuration as dict."""
        settings = self.get_settings()
        return settings.rag.dict()
    
    @property
    def system_prompt_template(self) -> str:
        """Get system prompt template."""
        return self.get_settings().llm.system_prompt_template
    
    @property
    def llm_provider(self) -> str:
        """Get LLM provider."""
        return self.get_settings().llm.provider
    
    @property
    def llm_model(self) -> str:
        """Get LLM model."""
        return self.get_settings().llm.model
    
    @property
    def llm_timeout(self) -> float:
        """Get LLM timeout."""
        return self.get_settings().llm.timeout
    
    def save_llm_config(self, provider: str, model: str) -> None:
        """Save LLM provider and model configuration."""
        settings = self.get_settings()
        settings.save_llm_config(provider, model)
        self.reload()
    
    def save_system_prompt_template(self, template: str) -> None:
        """Save system prompt template."""
        settings = self.get_settings()
        settings.save_system_prompt_template(template)
        self.reload()
    
    def save_config(self, system_prompt_template: str) -> None:
        """Save system prompt template."""
        settings = self.get_settings()
        settings.llm.system_prompt_template = system_prompt_template
        settings.save_to_yaml()
        self.reload()
    
    @property
    def _config(self) -> dict:
        """Legacy compatibility: access raw config dict."""
        # Load raw YAML for backward compatibility
        import yaml
        from pathlib import Path
        settings = self.get_settings()
        config_file = Path(settings.config_path)
        if config_file.exists():
            with open(config_file, "r", encoding="utf-8") as f:
                return yaml.safe_load(f) or {}
        return {}
    
    def _save_config(self) -> None:
        """Legacy compatibility: save config (delegates to Settings)."""
        settings = self.get_settings()
        settings.save_to_yaml()
        self.reload()


# Global configuration service instance
_config_service: Optional[ConfigurationService] = None


def get_config_service(config_path: Optional[str] = None) -> ConfigurationService:
    """
    Get global configuration service instance.
    
    Args:
        config_path: Optional config path (only used on first call)
        
    Returns:
        ConfigurationService instance
    """
    global _config_service
    if _config_service is None:
        _config_service = ConfigurationService(config_path)
    return _config_service


def reset_config_service() -> None:
    """Reset configuration service (useful for testing)."""
    global _config_service
    _config_service = None

