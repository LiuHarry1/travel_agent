"""Output guardrail for validating retrieval results."""
from __future__ import annotations

import logging
import re
from typing import Any, Dict, List, Optional

from app.service.rag.guardrails.base import BaseGuardrail, GuardrailResult
from app.service.rag.sources.base import RetrievalResult

logger = logging.getLogger(__name__)


class OutputGuardrail(BaseGuardrail):
    """Validates and filters retrieval results."""
    
    # Default sensitive patterns
    DEFAULT_SENSITIVE_PATTERNS = [
        r"sk-[a-zA-Z0-9]{20,}",  # OpenAI API key
        r"AKIA[0-9A-Z]{16}",  # AWS access key
        r"password\s*[:=]\s*['\"]?[^\s'\"]+",  # Password
        r"api[_-]?key\s*[:=]\s*['\"]?[^\s'\"]+",  # API key
        r"\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b",  # Credit card pattern
        r"\b\d{3}-\d{2}-\d{4}\b",  # SSN pattern
    ]
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize output guardrail."""
        super().__init__(config)
        self.max_results = config.get("max_results", 50)
        self.filter_sensitive_info = config.get("filter_sensitive_info", True)
        self.validate_relevance = config.get("validate_relevance", True)
        self.sensitive_patterns = config.get("sensitive_patterns", []) + self.DEFAULT_SENSITIVE_PATTERNS
    
    def validate(
        self,
        results: List[RetrievalResult],
        query: str
    ) -> GuardrailResult:
        """
        Validate retrieval results.
        
        Args:
            results: List of retrieval results
            query: Original query for relevance validation
            
        Returns:
            GuardrailResult with validation status and filtered results
        """
        if not self.enabled:
            return GuardrailResult(is_valid=True, filtered_results=results)
        
        filtered_results: List[RetrievalResult] = []
        issues: List[str] = []
        
        # Check 1: Result count limit
        if len(results) > self.max_results:
            issues.append(f"Too many results: {len(results)} (max: {self.max_results})")
            if self.strict_mode:
                return GuardrailResult(
                    is_valid=False,
                    reason=f"Too many results: {len(results)}",
                    filtered_results=[]
                )
            # Filter: keep top N
            filtered_results = results[:self.max_results]
            logger.warning(f"Output guardrail: Limited results from {len(results)} to {self.max_results}")
        else:
            filtered_results = list(results)
        
        # Check 2: Filter sensitive information
        if self.filter_sensitive_info:
            sanitized_count = 0
            for result in filtered_results:
                original_text = result.text
                sanitized_text = original_text
                
                # Check for sensitive patterns
                for pattern in self.sensitive_patterns:
                    if re.search(pattern, original_text):
                        # Mask sensitive information
                        sanitized_text = re.sub(pattern, "[REDACTED]", sanitized_text, flags=re.IGNORECASE)
                        sanitized_count += 1
                
                # If text was sanitized, create new result
                if sanitized_text != original_text:
                    # Create new result with sanitized text
                    sanitized_result = RetrievalResult(
                        chunk_id=result.chunk_id,
                        text=sanitized_text,
                        score=result.score,
                        metadata={**result.metadata, "sanitized": True}
                    )
                    filtered_results[filtered_results.index(result)] = sanitized_result
            
            if sanitized_count > 0:
                issues.append(f"Sanitized {sanitized_count} results with sensitive information")
                logger.warning(f"Output guardrail: Sanitized {sanitized_count} results")
        
        # Check 3: Validate relevance (simple check: ensure results have text)
        if self.validate_relevance:
            empty_results = [r for r in filtered_results if not r.text or not r.text.strip()]
            if empty_results:
                issues.append(f"Found {len(empty_results)} empty results")
                if self.strict_mode and len(empty_results) == len(filtered_results):
                    return GuardrailResult(
                        is_valid=False,
                        reason="All results are empty",
                        filtered_results=[]
                    )
                # Filter out empty results
                filtered_results = [r for r in filtered_results if r.text and r.text.strip()]
                logger.warning(f"Output guardrail: Filtered out {len(empty_results)} empty results")
        
        # Determine if validation passed
        is_valid = len(filtered_results) > 0 or not self.strict_mode
        
        return GuardrailResult(
            is_valid=is_valid,
            reason="; ".join(issues) if issues else None,
            filtered_results=filtered_results,
            metadata={
                "original_count": len(results),
                "filtered_count": len(filtered_results),
                "issues": issues
            }
        )

