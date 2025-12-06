"""Message processing logic for chat service."""
from __future__ import annotations

import logging
from typing import Dict, List

from ..models import ChatRequest
from ..utils.constants import MAX_CONVERSATION_TURNS
from .chat_file_handler import format_files_for_message

logger = logging.getLogger(__name__)


class MessageProcessingService:
    """Service for processing and formatting messages."""

    def __init__(self, config_getter):
        """Initialize message processing service."""
        self._get_config = config_getter
        self._mcp_registry = None

    def set_mcp_registry(self, mcp_registry):
        """Set MCP registry for tool information."""
        self._mcp_registry = mcp_registry

    def build_agent_system_prompt(self) -> str:
        """
        Build system prompt for travel agent.
        Uses configurable template from config.yaml with {tools} placeholder.
        If {tools} placeholder is present, it will be replaced with available tools list.
        If not present, tools will be appended at the end automatically.
        """
        try:
            config = self._get_config()
            template = config.system_prompt_template
        except (ValueError, FileNotFoundError) as e:
            logger.warning(f"Could not load system prompt from config: {e}. Using default prompt.")
            template = "You are a helpful travel agent assistant. Your goal is to help users with travel-related questions and planning."
        
        # Build tool list if tools are available
        tool_list = ""
        if self._mcp_registry:
            tools = self._mcp_registry.list_tools()
            if tools:
                tool_descriptions = []
                for tool in tools:
                    if isinstance(tool, dict):
                        tool_name = tool.get("name", "")
                        tool_desc = tool.get("description", "")
                    else:
                        tool_name = getattr(tool, 'name', '')
                        tool_desc = getattr(tool, 'description', '') or ""
                    tool_descriptions.append(f"- {tool_name}: {tool_desc}")
                tool_list = "\n".join(tool_descriptions)
        
        # Replace {tools} placeholder if present, otherwise append tools at the end
        if "{tools}" in template:
            prompt = template.replace("{tools}", tool_list if tool_list else "No tools available.")
        elif tool_list:
            # If no placeholder but tools exist, append at the end
            prompt = f"{template}\n\nAvailable Tools:\n{tool_list}"
        else:
            prompt = template
        
        logger.info(f"Generated system prompt (length: {len(prompt)} chars)")
        return prompt

    def trim_history(self, messages: List[Dict[str, str]], max_turns: int = MAX_CONVERSATION_TURNS) -> List[Dict[str, str]]:
        """
        Trim conversation history to keep only recent messages.
        
        Args:
            messages: Full conversation history
            max_turns: Maximum number of message turns to keep
            
        Returns:
            Trimmed conversation history
        """
        if len(messages) <= max_turns:
            return messages

        # Keep system message if exists, then recent messages
        if messages and messages[0].get("role") == "system":
            return [messages[0]] + messages[-(max_turns - 1):]
        return messages[-max_turns:]

    def prepare_messages(self, request: ChatRequest) -> List[Dict[str, str]]:
        """
        Prepare messages from request, including file handling.
        Filters out tool messages and tool_calls - only keeps user and assistant messages.
        
        Args:
            request: Chat request with message and files
            
        Returns:
            List of message dictionaries (only user and assistant, no tool messages)
        """
        # Handle file uploads - format as part of user message
        file_content = format_files_for_message(request.files)
        
        # Build user message
        user_message = request.message or ""
        if file_content:
            if user_message:
                user_message = f"{user_message}\n\n{file_content}"
            else:
                user_message = file_content

        # Get conversation history from request
        messages = request.messages or []
        
        # Filter out tool messages and tool_calls - only keep user and assistant messages
        # Also remove tool_calls from assistant messages
        filtered_messages = []
        for msg in messages:
            role = msg.get("role", "")
            # Only include user and assistant messages
            if role in ("user", "assistant"):
                # Create a clean message without tool_calls
                clean_msg = {
                    "role": role,
                    "content": msg.get("content", "") or ""  # Ensure content is always a string
                }
                # Explicitly exclude tool_calls, tool_call_id, name, etc.
                filtered_messages.append(clean_msg)
            # Skip tool messages (role == "tool")
        
        # Add current user message to history
        if user_message:
            filtered_messages.append({"role": "user", "content": user_message})

        # Trim history to keep it manageable
        return self.trim_history(filtered_messages)

