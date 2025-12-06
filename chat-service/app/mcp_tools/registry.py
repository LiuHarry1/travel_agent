"""MCP tool types for backward compatibility."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass
class ToolCall:
    """Represents a tool call request."""
    name: str
    arguments: Dict[str, Any]
    id: Optional[str] = None


@dataclass
class ToolResult:
    """Represents the result of a tool call."""
    tool_name: str
    success: bool
    result: Any
    error: Optional[str] = None
