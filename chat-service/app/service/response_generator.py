"""Response generation service for chat."""
from __future__ import annotations

import json
import logging
from typing import Any, AsyncGenerator, Dict, List, Optional, Tuple

from ..llm import LLMClient, LLMError
from ..tools import FunctionRegistry

logger = logging.getLogger(__name__)


class ResponseGenerator:
    """Generates streaming responses from LLM."""
    
    def __init__(
        self,
        llm_client: LLMClient,
        function_registry: FunctionRegistry
    ):
        """
        Initialize response generator.
        
        Args:
            llm_client: LLM client
            function_registry: Function registry
        """
        self.llm_client = llm_client
        self.function_registry = function_registry
    
    async def generate_response(
        self,
        messages: List[Dict[str, str]],
        system_prompt: str,
        functions: Optional[List[Dict[str, Any]]] = None
    ) -> AsyncGenerator[Tuple[str, Optional[Dict[str, Any]]], None]:
        """
        Generate streaming response from LLM.
        
        Args:
            messages: Conversation messages
            system_prompt: System prompt
            functions: Optional function definitions
            
        Yields:
            Tuples of (content_chunk, tool_call_info)
        """
        try:
            async for chunk, tool_call_info in self.llm_client.chat_stream_with_tools(
                messages=messages,
                system_prompt=system_prompt,
                functions=functions
            ):
                yield chunk, tool_call_info
        except LLMError as e:
            logger.error(f"LLM error during response generation: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error during response generation: {e}", exc_info=True)
            raise LLMError(f"Response generation failed: {str(e)}") from e
    
    def parse_tool_calls(
        self,
        tool_call_info: Optional[Dict[str, Any]]
    ) -> Optional[List[Dict[str, Any]]]:
        """
        Parse tool call information into structured format.
        
        Args:
            tool_call_info: Raw tool call info from LLM
            
        Returns:
            List of parsed tool calls or None
        """
        if not tool_call_info:
            return None
        
        tool_calls = []
        tool_calls_by_id: Dict[str, Dict[str, Any]] = {}
        
        # Handle both single and multiple tool calls
        if "id" in tool_call_info:
            # Single tool call
            tool_calls_by_id[tool_call_info["id"]] = tool_call_info
        elif "tool_calls" in tool_call_info:
            # Multiple tool calls
            for tc in tool_call_info["tool_calls"]:
                if "id" in tc:
                    tool_calls_by_id[tc["id"]] = tc
        
        # Convert to list format
        for call_id, call_data in tool_calls_by_id.items():
            try:
                function_data = call_data.get("function", {})
                tool_name = function_data.get("name", "")
                args_str = function_data.get("arguments", "{}")
                
                # Parse arguments
                try:
                    args = json.loads(args_str) if args_str else {}
                except json.JSONDecodeError:
                    logger.warning(f"Failed to parse tool arguments for {tool_name}: {args_str[:100]}")
                    args = {}
                
                tool_calls.append({
                    "id": call_id,
                    "function": {
                        "name": tool_name,
                        "arguments": args_str
                    }
                })
            except Exception as e:
                logger.error(f"Failed to parse tool call: {e}", exc_info=True)
        
        return tool_calls if tool_calls else None

