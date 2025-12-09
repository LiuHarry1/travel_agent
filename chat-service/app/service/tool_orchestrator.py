"""Tool orchestration service for coordinating tool calls."""
from __future__ import annotations

import logging
from typing import Any, AsyncGenerator, Dict, List, Optional

from ..tools import FunctionRegistry, ToolCall, ToolResult
from .tool_execution import ToolExecutionService

logger = logging.getLogger(__name__)


class ToolOrchestrator:
    """Orchestrates tool calls and manages tool execution flow."""
    
    def __init__(
        self,
        function_registry: FunctionRegistry,
        tool_executor: ToolExecutionService
    ):
        """
        Initialize tool orchestrator.
        
        Args:
            function_registry: Function registry
            tool_executor: Tool execution service
        """
        self.function_registry = function_registry
        self.tool_executor = tool_executor
    
    async def execute_tool_calls(
        self,
        tool_calls: List[Dict[str, Any]],
        messages: List[Dict[str, str]]
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Execute multiple tool calls and yield events.
        
        Args:
            tool_calls: List of tool call data from LLM
            messages: Conversation messages
            
        Yields:
            Tool execution events
        """
        # Use the existing execute_tool_calls method from ToolExecutionService
        async for event in self.tool_executor.execute_tool_calls(tool_calls, "", messages):
            yield event
    
    def should_continue_iteration(
        self,
        iteration: int,
        max_iterations: int,
        tool_calls: Optional[List[Dict[str, Any]]],
        has_content: bool
    ) -> bool:
        """
        Determine if tool iteration should continue.
        
        Args:
            iteration: Current iteration number
            max_iterations: Maximum iterations allowed
            tool_calls: Tool calls from current response
            has_content: Whether response has text content
            
        Returns:
            True if should continue, False otherwise
        """
        if iteration >= max_iterations:
            return False
        
        if tool_calls and len(tool_calls) > 0:
            return True
        
        if not has_content:
            # No content and no tool calls - might need another iteration
            return iteration < max_iterations
        
        return False

