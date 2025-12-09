"""Core exception classes for the application."""
from __future__ import annotations

from typing import Any, Dict, Optional


class ServiceError(Exception):
    """Base exception for service layer errors."""
    
    def __init__(
        self,
        message: str,
        code: str = "SERVICE_ERROR",
        details: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize service error.
        
        Args:
            message: Error message
            code: Error code for programmatic handling
            details: Additional error details
        """
        self.message = message
        self.code = code
        self.details = details or {}
        super().__init__(self.message)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert error to dictionary."""
        result = {
            "error": self.message,
            "code": self.code
        }
        if self.details:
            result["details"] = self.details
        return result


class ConfigurationError(ServiceError):
    """Exception raised when configuration is invalid."""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, code="CONFIG_ERROR", details=details)


class RAGError(ServiceError):
    """Exception raised when RAG operations fail."""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, code="RAG_ERROR", details=details)


class LLMError(ServiceError):
    """Exception raised when LLM operations fail."""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, code="LLM_ERROR", details=details)


class ToolExecutionError(ServiceError):
    """Exception raised when tool execution fails."""
    
    def __init__(self, message: str, tool_name: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        if details is None:
            details = {}
        if tool_name:
            details["tool_name"] = tool_name
        super().__init__(message, code="TOOL_EXECUTION_ERROR", details=details)


class ValidationError(ServiceError):
    """Exception raised when validation fails."""
    
    def __init__(self, message: str, field: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        if details is None:
            details = {}
        if field:
            details["field"] = field
        super().__init__(message, code="VALIDATION_ERROR", details=details)

