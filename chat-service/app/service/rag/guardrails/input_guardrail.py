"""Input guardrail for validating user queries."""
from __future__ import annotations

import logging
import re
from typing import Dict, List, Optional

from app.service.rag.guardrails.base import BaseGuardrail, GuardrailResult

logger = logging.getLogger(__name__)


class InputGuardrail(BaseGuardrail):
    """Validates and sanitizes user input queries."""
    
    # Default blocked patterns (prompt injection, SQL injection, etc.)
    DEFAULT_BLOCKED_PATTERNS = [
        r"(?i)ignore\s+(previous|all|above)\s+instructions?",
        r"(?i)forget\s+(previous|all|everything)",
        r"(?i)you\s+are\s+now",
        r"(?i)system\s*:",
        r"(?i)assistant\s*:",
        r"(?i)new\s+instructions?",
        r"(?i)disregard\s+(previous|all)",
        r"(?i)override",
        r"(?i)delete\s+(all|everything)",
        r"(?i)drop\s+table",
        r"(?i)union\s+select",
        r"(?i);\s*drop",
        r"(?i)exec\s*\(",
        r"(?i)script\s*>",
    ]
    
    # Default sensitive patterns (API keys, passwords, etc.)
    DEFAULT_SENSITIVE_PATTERNS = [
        r"sk-[a-zA-Z0-9]{20,}",  # OpenAI API key pattern
        r"AKIA[0-9A-Z]{16}",  # AWS access key
        r"password\s*[:=]\s*['\"]?[^\s'\"]+",  # Password pattern
        r"api[_-]?key\s*[:=]\s*['\"]?[^\s'\"]+",  # API key pattern
    ]
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize input guardrail."""
        super().__init__(config)
        self.max_query_length = config.get("max_query_length", 1000)
        self.blocked_patterns = config.get("blocked_patterns", []) + self.DEFAULT_BLOCKED_PATTERNS
        self.sensitive_patterns = config.get("sensitive_patterns", []) + self.DEFAULT_SENSITIVE_PATTERNS
    
    def validate(
        self,
        query: str,
        conversation_history: Optional[List[Dict]] = None
    ) -> GuardrailResult:
        """
        Validate user query.
        
        Args:
            query: User query string
            conversation_history: Optional conversation history
            
        Returns:
            GuardrailResult with validation status
        """
        if not self.enabled:
            return GuardrailResult(is_valid=True, sanitized_content=query)
        
        # Check 1: Length validation
        if len(query) > self.max_query_length:
            reason = f"Query too long: {len(query)} characters (max: {self.max_query_length})"
            logger.warning(f"Input guardrail: {reason}")
            if self.strict_mode:
                return GuardrailResult(is_valid=False, reason=reason)
            # Sanitize: truncate
            sanitized = query[:self.max_query_length]
            return GuardrailResult(
                is_valid=True,
                reason="Query truncated due to length",
                sanitized_content=sanitized,
                metadata={"truncated": True, "original_length": len(query)}
            )
        
        # Check 2: Blocked patterns
        for pattern in self.blocked_patterns:
            if re.search(pattern, query):
                reason = f"Query contains blocked pattern: {pattern[:50]}"
                logger.warning(f"Input guardrail: {reason}")
                if self.strict_mode:
                    return GuardrailResult(is_valid=False, reason=reason)
                # Sanitize: remove the pattern
                sanitized = re.sub(pattern, "", query, flags=re.IGNORECASE).strip()
                if not sanitized:
                    sanitized = query  # Fallback to original if sanitization removes everything
                return GuardrailResult(
                    is_valid=True,
                    reason="Query sanitized due to blocked pattern",
                    sanitized_content=sanitized,
                    metadata={"sanitized": True, "pattern": pattern[:50]}
                )
        
        # Check 3: Sensitive information
        for pattern in self.sensitive_patterns:
            if re.search(pattern, query):
                reason = f"Query may contain sensitive information: {pattern[:50]}"
                logger.warning(f"Input guardrail: {reason}")
                if self.strict_mode:
                    return GuardrailResult(is_valid=False, reason=reason)
                # Sanitize: mask sensitive info
                sanitized = re.sub(pattern, "[REDACTED]", query, flags=re.IGNORECASE)
                return GuardrailResult(
                    is_valid=True,
                    reason="Query sanitized due to sensitive information",
                    sanitized_content=sanitized,
                    metadata={"sanitized": True, "sensitive_pattern": pattern[:50]}
                )
        
        # All checks passed
        return GuardrailResult(is_valid=True, sanitized_content=query)




