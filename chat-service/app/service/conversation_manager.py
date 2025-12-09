"""Conversation state management service."""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from ..models import ChatRequest
from ..utils.constants import MAX_CONVERSATION_TURNS
from .chat_file_handler import format_files_for_message
from .message_processing import MessageProcessingService

logger = logging.getLogger(__name__)


class ConversationManager:
    """Manages conversation state and message preparation."""
    
    def __init__(self, message_processor: MessageProcessingService):
        """
        Initialize conversation manager.
        
        Args:
            message_processor: Message processing service
        """
        self.message_processor = message_processor
    
    def prepare_conversation(self, request: ChatRequest) -> Dict[str, Any]:
        """
        Prepare conversation from request.
        
        Args:
            request: Chat request
            
        Returns:
            Dict with messages, system_prompt, and metadata
        """
        # Prepare messages from request
        messages = self.message_processor.prepare_messages(request)
        
        # Build system prompt
        system_prompt = self.message_processor.build_agent_system_prompt()
        
        # Get function definitions
        function_registry = self.message_processor._function_registry
        functions = []
        if function_registry:
            functions = function_registry.get_function_definitions_for_llm()
        
        return {
            "messages": messages,
            "system_prompt": system_prompt,
            "functions": functions,
            "has_messages": len(messages) > 0
        }
    
    def add_tool_result(
        self,
        messages: List[Dict[str, str]],
        tool_call_id: str,
        tool_name: str,
        tool_content: str
    ) -> None:
        """
        Add tool result to conversation.
        
        Args:
            messages: Conversation messages (modified in place)
            tool_call_id: Tool call ID
            tool_name: Tool name
            tool_content: Formatted tool result content
        """
        tool_message = {
            "role": "tool",
            "tool_call_id": tool_call_id,
            "name": tool_name,
            "content": tool_content
        }
        messages.append(tool_message)
    
    def add_assistant_message(
        self,
        messages: List[Dict[str, str]],
        content: str,
        tool_calls: Optional[List[Dict[str, Any]]] = None
    ) -> None:
        """
        Add assistant message to conversation.
        
        Args:
            messages: Conversation messages (modified in place)
            content: Message content
            tool_calls: Optional tool calls
        """
        assistant_msg: Dict[str, Any] = {
            "role": "assistant",
            "content": content
        }
        if tool_calls:
            assistant_msg["tool_calls"] = tool_calls
        messages.append(assistant_msg)
    
    def truncate_conversation(self, messages: List[Dict[str, str]]) -> List[Dict[str, str]]:
        """
        Truncate conversation to max turns.
        
        Args:
            messages: Conversation messages
            
        Returns:
            Truncated messages
        """
        # Keep system message and last N turns
        if len(messages) <= MAX_CONVERSATION_TURNS * 2:  # Each turn has user + assistant
            return messages
        
        # Keep first message (usually system) and last N turns
        truncated = messages[:1]  # Keep first
        truncated.extend(messages[-(MAX_CONVERSATION_TURNS * 2):])  # Keep last N turns
        return truncated

