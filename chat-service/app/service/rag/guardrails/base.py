"""Base classes for guardrails."""
from __future__ import annotations

from abc import ABC
from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass
class GuardrailResult:
    """Result from guardrail validation."""
    is_valid: bool
    reason: Optional[str] = None
    sanitized_content: Optional[str] = None
    filtered_results: Optional[List[Any]] = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class BaseGuardrail(ABC):
    """Base class for all guardrails."""
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize guardrail.
        
        Args:
            config: Guardrail configuration
        """
        self.config = config
        self.enabled = config.get("enabled", True)
        self.strict_mode = config.get("strict_mode", False)




