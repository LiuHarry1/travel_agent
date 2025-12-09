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
        self._function_registry = None

    def set_function_registry(self, function_registry):
        """Set function registry for tool information."""
        self._function_registry = function_registry

    def build_agent_system_prompt(self) -> str:
        """
        Build system prompt for travel agent with RAG optimization support.
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
        enabled_functions = []
        
        if self._function_registry:
            functions = self._function_registry.get_all_functions()
            enabled_functions = [f.name for f in functions if f.enabled]
            if functions:
                tool_descriptions = []
                for func_def in functions:
                    if func_def.enabled:
                        tool_descriptions.append(f"- {func_def.name}: {func_def.description}")
                tool_list = "\n".join(tool_descriptions)
        
        # Replace {tools} placeholder if present, otherwise append tools at the end
        if "{tools}" in template:
            prompt = template.replace("{tools}", tool_list if tool_list else "No tools available.")
        elif tool_list:
            # If no placeholder but tools exist, append at the end
            prompt = f"{template}\n\nAvailable Tools:\n{tool_list}"
        else:
            prompt = template
        
        # 如果启用了 retrieval_service_search，添加 RAG 优化指导
        if self._function_registry and "retrieval_service_search" in enabled_functions:
            rag_guidance = """

**RAG 检索优化策略：**

1. **理解上下文**：
   - 仔细分析当前用户问题
   - 回顾历史对话，提取相关信息（地点、时间、主题、实体等）
   - 识别问题的核心意图

2. **生成优化查询**：
   - 将用户问题转换为更易检索的查询
   - 结合历史对话中的上下文信息
   - 如果问题模糊，先检索广泛信息，再根据结果深入检索
   - 查询应该具体、包含关键实体（2-10 个词）

3. **多轮检索策略**：
   - 第一次检索：基于用户问题和历史上下文生成查询
   - 如果检索结果不够充分，可以：
     a) 从不同角度再次检索（补充关键词、细化查询）
     b) 检索更具体的信息（如特定步骤、详细要求）
     c) 检索相关的背景信息（如相关主题、前置条件）
   - 最多可以检索 2-3 次，确保信息充分
   - 每次检索后，评估结果是否足够回答问题

4. **使用检索结果**：
   - 综合所有检索结果
   - 基于文档内容回答问题
   - 引用文档来源（chunk_id）
   - 如果文档中没有相关信息，明确告知用户
   - 不要编造信息，只基于检索到的文档回答

**示例场景：**

场景 1：简单问题
- 用户："日本签证需要什么材料？"
- 查询："日本签证申请材料要求"
- 检索 1 次即可

场景 2：需要上下文
- 历史："我想去日本旅游"
- 用户："需要什么材料？"
- 查询："日本旅游签证申请材料"（结合历史上下文）

场景 3：复杂问题，需要多轮检索
- 用户："日本签证办理流程和材料"
- 第一次查询："日本签证办理流程"
- 如果结果不够，第二次查询："日本签证申请材料清单"
- 综合两次结果回答
"""
            prompt = f"{prompt}\n{rag_guidance}"
        
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
        # 保留足够的历史对话用于上下文感知（最多 10 轮）
        filtered_messages = []
        for msg in messages[-10:]:  # 保留最近 10 轮对话用于上下文感知
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

