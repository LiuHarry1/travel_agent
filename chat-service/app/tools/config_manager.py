"""Configuration manager for function registry."""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

logger = logging.getLogger(__name__)


class ConfigManager:
    """Manages configuration persistence for function registry."""
    
    def __init__(self, config_path: Path):
        """
        Initialize config manager.
        
        Args:
            config_path: Path to configuration file
        """
        self.config_path = config_path
    
    def save(
        self,
        enabled_functions: List[str],
        function_configs: Dict[str, Dict[str, Any]]
    ) -> None:
        """
        Save configuration to file.
        
        Args:
            enabled_functions: List of enabled function names
            function_configs: Dict mapping function names to their configs
        """
        try:
            config = {
                "functions": {
                    "enabled": enabled_functions,
                    "configs": function_configs
                }
            }
            
            # Ensure directory exists
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(self.config_path, "w", encoding="utf-8") as f:
                yaml.dump(config, f, allow_unicode=True, default_flow_style=False)
            
            logger.info(f"Saved function registry config to {self.config_path}")
        except Exception as e:
            logger.error(f"Failed to save function registry config: {e}", exc_info=True)
            raise
    
    def load(self) -> tuple[List[str], Dict[str, Dict[str, Any]]]:
        """
        Load configuration from file.
        
        Returns:
            Tuple of (enabled_functions, function_configs)
        """
        if not self.config_path.exists():
            logger.warning(f"Function config file not found: {self.config_path}")
            return [], {}
        
        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                config = yaml.safe_load(f) or {}
            
            enabled = config.get("functions", {}).get("enabled", [])
            configs = config.get("functions", {}).get("configs", {})
            
            logger.info(f"Loaded function registry config from {self.config_path}")
            return enabled, configs
        except Exception as e:
            logger.error(f"Failed to load function registry config: {e}", exc_info=True)
            return [], {}

