"""Chat service for conversational travel agent with MCP tool calling."""
from __future__ import annotations

import asyncio
import json
import logging
import sys
import time
from typing import Any, Dict, Generator, List, Optional, Tuple

from ..config import get_config
from ..llm import LLMClient, LLMError
from ..mcp import MCPToolRegistry, ToolCall, ToolResult
from ..models import ChatRequest
from ..utils.constants import MAX_CONVERSATION_TURNS
from ..utils.exceptions import format_error_message
from .chat_file_handler import format_files_for_message

logger = logging.getLogger(__name__)


class ChatService:
    """Service for conversational travel agent with MCP tool calling."""

    def __init__(self, llm_client: Optional[LLMClient] = None, mcp_registry: Optional[MCPToolRegistry] = None):
        """Initialize chat service."""
        self.llm_client = llm_client or LLMClient()
        self.mcp_registry = mcp_registry or MCPToolRegistry()
        self.max_tool_iterations = 5

    def _build_agent_system_prompt(self) -> str:
        """
        Build system prompt for travel agent.
        Reads base prompt from config.yaml (user-configurable) and adds available tools dynamically.
        Tool descriptions come from MCP tool schemas (get_input_schema), which contain detailed usage instructions.
        No hardcoded tool names or usage guidelines - everything is dynamic and tool-agnostic.
        """
        # Get base system prompt template from config (user-configurable via UI)
        try:
            config = get_config()
            base_prompt = config.system_prompt_template
        except (ValueError, FileNotFoundError) as e:
            logger.warning(f"Could not load system prompt from config: {e}. Using default prompt.")
            base_prompt = "You are a helpful travel agent assistant. Your goal is to help users with travel-related questions and planning."
        
        # Get available tools from MCP servers (loaded dynamically - no hardcoded tool names)
        tools = self.mcp_registry.list_tools()
        
        if not tools:
            # No tools available, return base prompt only
            return base_prompt
        
        # Build tool list with detailed descriptions
        # Tool descriptions come from MCP tool schemas and contain usage instructions
        # All tool-specific usage information is in the tool descriptions themselves
        tool_descriptions = []
        for tool in tools:
            # Get detailed description from tool schema
            tool_name = tool.name
            tool_desc = tool.description or ""
            
            # Get parameter descriptions from input schema for additional context
            # Parameter descriptions often contain important usage hints
            # MCPToolConfig stores inputSchema in extra kwargs
            input_schema = getattr(tool, 'inputSchema', None) or getattr(tool, 'extra', {}).get('inputSchema', {})
            param_descriptions = []
            
            if isinstance(input_schema, dict):
                properties = input_schema.get("properties", {})
                for param_name, param_info in properties.items():
                    if isinstance(param_info, dict) and "description" in param_info:
                        param_desc = param_info["description"]
                        # Include parameter descriptions that contain usage hints (longer descriptions)
                        if param_desc and len(param_desc) > 50:
                            param_descriptions.append(f"  - {param_name}: {param_desc}")
            
            # Build tool entry
            tool_entry = f"- {tool_name}: {tool_desc}"
            if param_descriptions:
                # Include parameter descriptions that contain usage hints
                tool_entry += "\n" + "\n".join(param_descriptions)
            
            tool_descriptions.append(tool_entry)
        
        tool_list = "\n".join(tool_descriptions)
        
        # Append tools section to base prompt
        # All tool-specific usage instructions are in the tool descriptions themselves
        # No hardcoded tool names or usage guidelines - fully dynamic
        prompt = f"""{base_prompt}

Available Tools:
{tool_list}

Use the available tools when you need specific information to answer user questions. Each tool's description and parameters contain detailed usage instructions.

Important: If you have tried using the available tools but still cannot provide a helpful answer to the user's travel-related question, politely inform the user that you could not find the information and suggest they contact Harry for more specific assistance."""
        
        logger.info(f"Generated system prompt: {prompt}")
        return prompt

    def _trim_history(self, messages: List[Dict[str, str]], max_turns: int = MAX_CONVERSATION_TURNS) -> List[Dict[str, str]]:
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

    def _prepare_messages(self, request: ChatRequest) -> List[Dict[str, str]]:
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
        return self._trim_history(filtered_messages)

    def _normalize_tool_calls(self, assistant_message: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Normalize tool calls from different LLM formats (function_call vs tool_calls).
        
        Args:
            assistant_message: Assistant message from LLM response
            
        Returns:
            List of normalized tool call dictionaries
        """
        # DashScope/Qwen uses "function_call" (singular) instead of "tool_calls" (plural)
        # OpenAI format uses "tool_calls" (plural)
        function_call = assistant_message.get("function_call")
        tool_calls = assistant_message.get("tool_calls", [])
        
        # Convert function_call to tool_calls format for consistency
        if function_call and not tool_calls:
            # DashScope format: single function_call
            tool_calls = [{
                "id": function_call.get("id", f"call_{int(time.time() * 1000)}"),
                "function": {
                    "name": function_call.get("name", ""),
                    "arguments": function_call.get("arguments", "{}")
                },
                "type": "function"
            }]
            logger.info(f"Converted function_call to tool_calls format: {function_call.get('name', 'unknown')}")
        
        return tool_calls or []

    def _detect_tool_calls(self, messages: List[Dict[str, str]], system_prompt: str, functions: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """
        Detect tool calls by making a non-streaming LLM request.
        
        Args:
            messages: Conversation messages
            system_prompt: System prompt for the LLM
            functions: Available function definitions
            
        Returns:
            Dict with 'content' and 'tool_calls' keys, or None if error
        """
        # Ensure proper event loop for Windows compatibility
        self._ensure_event_loop()
        
        # Suppress asyncio resource warnings on Windows during tool detection
        if sys.platform == "win32":
            import warnings
            with warnings.catch_warnings():
                warnings.filterwarnings("ignore", category=ResourceWarning, message=".*unclosed.*")
                warnings.filterwarnings("ignore", message=".*Event loop is closed.*")
                warnings.filterwarnings("ignore", message=".*I/O operation on closed pipe.*")
                try:
                    return self._detect_tool_calls_impl(messages, system_prompt, functions)
                except Exception as e:
                    logger.error(f"Error in tool detection call: {e}", exc_info=True)
                    return None
        else:
            try:
                return self._detect_tool_calls_impl(messages, system_prompt, functions)
            except Exception as e:
                logger.error(f"Error in tool detection call: {e}", exc_info=True)
                return None
    
    def _detect_tool_calls_impl(self, messages: List[Dict[str, str]], system_prompt: str, functions: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """
        Internal implementation of tool detection.
        
        Args:
            messages: Conversation messages
            system_prompt: System prompt for the LLM
            functions: Available function definitions
            
        Returns:
            Dict with 'content' and 'tool_calls' keys, or None if error
        """
        start_time = time.time()
        try:
            client = self.llm_client._get_client()
            system_msg = {"role": "system", "content": system_prompt}
            all_messages = [system_msg] + messages
            
            payload_start = time.time()
            payload = client._normalize_payload(all_messages, model=client.model)
            payload["functions"] = functions
            payload["function_call"] = "auto"
            payload["max_tokens"] = 300  # Reduced from 500 to 300 for faster tool detection (only needs tool name and args)
            payload_time = time.time() - payload_start
            logger.info(f"[PERF] Tool detection payload preparation took {payload_time:.3f}s")
            
            logger.info(f"Making tool detection request with {len(functions)} functions")
            logger.debug(f"Payload: {json.dumps(payload, ensure_ascii=False, indent=2)[:500]}")
            
            request_start = time.time()
            response_data = client._make_request("chat/completions", payload)
            request_time = time.time() - request_start
            logger.info(f"[PERF] Tool detection LLM request took {request_time:.3f}s")
            logger.info(f"Received response, keys: {list(response_data.keys())}")
            
            parse_start = time.time()
            if "choices" not in response_data or not response_data["choices"]:
                logger.error(f"Invalid response format: {response_data}")
                return None
            
            assistant_message = response_data.get("choices", [{}])[0].get("message", {})
            logger.info(f"Assistant message keys: {list(assistant_message.keys())}")
            
            content = assistant_message.get("content") or assistant_message.get("text", "")
            tool_calls = self._normalize_tool_calls(assistant_message)
            parse_time = time.time() - parse_start
            logger.info(f"[PERF] Tool detection response parsing took {parse_time:.3f}s")
            
            logger.info(f"Content: {content[:100] if content else 'None'}, Tool calls: {len(tool_calls)}")
            
            if tool_calls:
                tool_names = [self._extract_tool_name(tc) for tc in tool_calls]
                logger.info(f"Tool calls detected: {tool_names}")
            
            total_time = time.time() - start_time
            logger.info(f"[PERF] Total tool detection took {total_time:.3f}s (payload: {payload_time:.3f}s, request: {request_time:.3f}s, parse: {parse_time:.3f}s)")
            
            return {
                "content": content,
                "tool_calls": tool_calls
            }
        except Exception as e:
            total_time = time.time() - start_time
            logger.error(f"[PERF] Tool detection failed after {total_time:.3f}s: {e}", exc_info=True)
            return None

    def _extract_tool_name(self, tool_call: Any) -> str:
        """Extract tool name from tool call data structure."""
        if isinstance(tool_call, dict):
            func_info = tool_call.get("function", {})
            if isinstance(func_info, dict):
                return func_info.get("name", "unknown")
            return str(func_info)
        return str(tool_call)

    def _format_tool_result_for_llm(self, tool_result: Any, tool_name: str) -> str:
        """
        Format tool result for LLM consumption.
        
        Args:
            tool_result: Tool execution result (can be str, dict, or other)
            tool_name: Name of the tool (for logging)
            
        Returns:
            Formatted string content for LLM
        """
        if isinstance(tool_result, str):
            logger.debug(f"Tool {tool_name} returned string result (length: {len(tool_result)})")
            return tool_result
        elif isinstance(tool_result, dict):
            # If it's a dict, check if it has a 'text' key (from MCPClient fallback)
            if "text" in tool_result:
                logger.debug(f"Tool {tool_name} returned dict with 'text' key (length: {len(tool_result['text'])})")
                return tool_result["text"]
            
            # Special handling for FAQ tool: check if answer was found
            if tool_name == "faq" and ("found" in tool_result or tool_result.get("answer") is None):
                # FAQ didn't find an answer - format clearly for LLM
                found = tool_result.get("found", tool_result.get("answer") is not None)
                message = tool_result.get("message", "FAQ知识库中没有找到匹配的答案。")
                
                if not found:
                    # Format as clear message that FAQ didn't find answer
                    formatted = f"FAQ工具结果: {message}\n建议: 可以尝试使用retriever工具在知识库中搜索相关信息。"
                    logger.info(f"Tool {tool_name} did not find answer, formatted for LLM: {formatted[:100]}")
                    return formatted
            
            # Special handling for retriever tool: check if results are empty
            if tool_name == "retriever" and "results" in tool_result:
                results = tool_result.get("results", [])
                if not results or len(results) == 0:
                    # No results found - format clearly for LLM
                    formatted = "Retriever工具结果: 在知识库中没有找到相关信息。\n建议: 如果FAQ和Retriever工具都没有找到有用信息，可以提醒用户联系Harry获取更具体的帮助。"
                    logger.info(f"Tool {tool_name} found no results, formatted for LLM")
                    return formatted
            
            # Otherwise, serialize the dict as JSON
            content = json.dumps(tool_result, ensure_ascii=False)
            logger.debug(f"Tool {tool_name} returned dict (serialized length: {len(content)}, keys: {list(tool_result.keys())})")
            return content
        else:
            # Fallback: convert to string
            content = str(tool_result)
            logger.debug(f"Tool {tool_name} returned non-string/dict result (converted length: {len(content)})")
            return content

    def _check_tools_used_but_no_info(self, messages: List[Dict[str, str]]) -> bool:
        """
        Check if tools were used but didn't find useful information.
        
        Args:
            messages: Conversation messages
            
        Returns:
            True if tools were used but didn't find useful information
        """
        tool_messages = [msg for msg in messages if msg.get("role") == "tool"]
        if not tool_messages:
            return False
        
        # Check if any tool message indicates no useful information was found
        for msg in tool_messages:
            content = msg.get("content", "")
            # Check for indicators that tools didn't find useful information
            if any(indicator in content for indicator in [
                "没有找到",
                "没有找到匹配",
                "没有找到相关信息",
                "未能找到",
                "找不到",
                "无法找到"
            ]):
                return True
        
        return False
    
    def _response_suggests_contact_harry(self, content: str) -> bool:
        """
        Check if the response already suggests contacting Harry.
        
        Args:
            content: Response content
            
        Returns:
            True if response already suggests contacting Harry
        """
        harry_indicators = ["联系Harry", "联系harry", "联系 Harry", "联系 harry", "contact Harry", "contact harry"]
        return any(indicator in content for indicator in harry_indicators)

    def _ensure_event_loop(self) -> asyncio.AbstractEventLoop:
        """Ensure proper event loop is set up for Windows compatibility."""
        if sys.platform == "win32":
            if hasattr(asyncio, "WindowsProactorEventLoopPolicy"):
                asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
        
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        return loop

    def _execute_single_tool(self, tool_call_data: Dict[str, Any], messages: List[Dict[str, str]]) -> Generator[Dict[str, Any], None, None]:
        """
        Execute a single tool call and yield events.
        
        Args:
            tool_call_data: Tool call data from LLM
            messages: Conversation messages (will be updated with tool result)
            
        Yields:
            Tool call events (start, end, or error)
        """
        tool_start_time = time.time()
        tool_call_id = tool_call_data.get("id", "")
        tool_name = tool_call_data.get("function", {}).get("name", "")
        tool_args_str = tool_call_data.get("function", {}).get("arguments", "{}")
        
        # Parse arguments
        try:
            tool_args = json.loads(tool_args_str)
        except json.JSONDecodeError:
            logger.warning(f"Failed to parse tool arguments: {tool_args_str}")
            tool_args = {}
        
        # Yield tool call start event
        logger.info(f"Yielding tool_call_start event for tool: {tool_name}, id: {tool_call_id}")
        yield {
            "type": "tool_call_start",
            "tool": tool_name,
            "tool_call_id": tool_call_id,
            "input": tool_args
        }
        
        # Execute tool
        tool_call = ToolCall(
            name=tool_name,
            arguments=tool_args,
            id=tool_call_id
        )
        
        try:
            exec_start = time.time()
            loop = self._ensure_event_loop()
            tool_result = loop.run_until_complete(
                self.mcp_registry.call_tool(tool_call)
            )
            exec_time = time.time() - exec_start
            logger.info(f"[PERF] Tool '{tool_name}' execution took {exec_time:.3f}s")
            
            if tool_result.success:
                # Yield tool call end event
                yield {
                    "type": "tool_call_end",
                    "tool": tool_name,
                    "tool_call_id": tool_call_id,
                    "result": tool_result.result
                }
                
                # Format tool result content for LLM
                format_start = time.time()
                tool_content = self._format_tool_result_for_llm(tool_result.result, tool_name)
                format_time = time.time() - format_start
                logger.info(f"[PERF] Tool '{tool_name}' result formatting took {format_time:.3f}s, content length: {len(tool_content)} chars")
                logger.debug(f"Tool {tool_name} result preview (first 200 chars): {tool_content[:200]}")
                
                # Add tool result to messages (LLM will decide if more tools are needed based on this result)
                tool_message = {
                    "role": "tool",
                    "tool_call_id": tool_call_id,
                    "name": tool_name,
                    "content": tool_content
                }
                messages.append(tool_message)
                logger.debug(f"Added tool message to conversation: role={tool_message['role']}, tool_call_id={tool_call_id}, name={tool_name}, content_length={len(tool_content)}")
            else:
                # Yield tool call error event
                error_msg = tool_result.error or "Unknown error"
                yield {
                    "type": "tool_call_error",
                    "tool": tool_name,
                    "tool_call_id": tool_call_id,
                    "error": error_msg
                }
                
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call_id,
                    "name": tool_name,
                    "content": f"Error: {error_msg}"
                })
            tool_total_time = time.time() - tool_start_time
            logger.info(f"[PERF] Tool '{tool_name}' total execution (with error handling) took {tool_total_time:.3f}s")
        except Exception as e:
            tool_total_time = time.time() - tool_start_time
            logger.error(f"[PERF] Tool '{tool_name}' failed after {tool_total_time:.3f}s: {e}", exc_info=True)
            yield {
                "type": "tool_call_error",
                "tool": tool_name,
                "tool_call_id": tool_call_id,
                "error": str(e)
            }
            messages.append({
                "role": "tool",
                "tool_call_id": tool_call_id,
                "name": tool_name,
                "content": f"Error: {str(e)}"
            })

    def _execute_tool_calls(self, tool_calls: List[Dict[str, Any]], content: str, messages: List[Dict[str, str]]) -> Generator[Dict[str, Any], None, None]:
        """
        Execute multiple tool calls and yield events.
        
        If multiple tools are detected, they will be executed in parallel for better performance.
        
        Args:
            tool_calls: List of tool call data from LLM
            content: Assistant message content
            messages: Conversation messages (will be updated with tool results)
            
        Yields:
            Tool call events for each tool
        """
        # Add assistant message with tool calls to history
        messages.append({
            "role": "assistant",
            "content": content,
            "tool_calls": tool_calls
        })
        
        # If multiple tools, execute in parallel for better performance
        if len(tool_calls) > 1:
            logger.info(f"[PERF] Executing {len(tool_calls)} tools in parallel")
            # Execute tools in parallel
            yield from self._execute_tools_parallel(tool_calls, messages)
        else:
            # Single tool, execute sequentially
            for tool_call_data in tool_calls:
                yield from self._execute_single_tool(tool_call_data, messages)
    
    def _execute_tools_parallel(self, tool_calls: List[Dict[str, Any]], messages: List[Dict[str, str]]) -> Generator[Dict[str, Any], None, None]:
        """
        Execute multiple tool calls in parallel and yield events in order.
        
        Args:
            tool_calls: List of tool call data from LLM
            messages: Conversation messages (will be updated with tool results)
            
        Yields:
            Tool call events for each tool (in the order they complete)
        """
        async def execute_tool_async(tool_call_data: Dict[str, Any]) -> List[Dict[str, Any]]:
            """Execute a single tool asynchronously and collect all events."""
            events = []
            # Create a temporary messages list for this tool to avoid race conditions
            tool_messages = []
            
            tool_call_id = tool_call_data.get("id", "")
            tool_name = tool_call_data.get("function", {}).get("name", "")
            tool_args_str = tool_call_data.get("function", {}).get("arguments", "{}")
            
            # Parse arguments
            try:
                tool_args = json.loads(tool_args_str)
            except json.JSONDecodeError:
                logger.warning(f"Failed to parse tool arguments: {tool_args_str}")
                tool_args = {}
            
            # Note: Start event is yielded separately before parallel execution
            # to maintain order. We only collect end/error events here.
            
            # Execute tool
            tool_call = ToolCall(
                name=tool_name,
                arguments=tool_args,
                id=tool_call_id
            )
            
            try:
                exec_start = time.time()
                tool_result = await self.mcp_registry.call_tool(tool_call)
                exec_time = time.time() - exec_start
                logger.info(f"[PERF] Tool '{tool_name}' execution (parallel) took {exec_time:.3f}s")
                
                if tool_result.success:
                    # Yield tool call end event
                    events.append({
                        "type": "tool_call_end",
                        "tool": tool_name,
                        "tool_call_id": tool_call_id,
                        "result": tool_result.result
                    })
                    
                    # Format tool result content for LLM
                    format_start = time.time()
                    tool_content = self._format_tool_result_for_llm(tool_result.result, tool_name)
                    format_time = time.time() - format_start
                    logger.info(f"[PERF] Tool '{tool_name}' result formatting took {format_time:.3f}s, content length: {len(tool_content)} chars")
                    
                    # Store tool message for later addition to messages (LLM will decide if more tools are needed)
                    tool_messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call_id,
                        "name": tool_name,
                        "content": tool_content
                    })
                else:
                    # Yield tool call error event
                    error_msg = tool_result.error or "Unknown error"
                    events.append({
                        "type": "tool_call_error",
                        "tool": tool_name,
                        "tool_call_id": tool_call_id,
                        "error": error_msg
                    })
                    
                    tool_messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call_id,
                        "name": tool_name,
                        "content": f"Error: {error_msg}"
                    })
            except Exception as e:
                logger.error(f"[PERF] Tool '{tool_name}' failed: {e}", exc_info=True)
                events.append({
                    "type": "tool_call_error",
                    "tool": tool_name,
                    "tool_call_id": tool_call_id,
                    "error": str(e)
                })
                
                tool_messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call_id,
                    "name": tool_name,
                    "content": f"Error: {str(e)}"
                })
            
            return events, tool_messages
        
        # Execute all tools in parallel
        loop = self._ensure_event_loop()
        try:
            # First, yield all start events in order
            for tool_call_data in tool_calls:
                tool_call_id = tool_call_data.get("id", "")
                tool_name = tool_call_data.get("function", {}).get("name", "")
                tool_args_str = tool_call_data.get("function", {}).get("arguments", "{}")
                try:
                    tool_args = json.loads(tool_args_str)
                except json.JSONDecodeError:
                    tool_args = {}
                
                yield {
                    "type": "tool_call_start",
                    "tool": tool_name,
                    "tool_call_id": tool_call_id,
                    "input": tool_args
                }
            
            # Create tasks for all tools and execute in parallel
            tasks = [execute_tool_async(tc) for tc in tool_calls]
            # Wait for all tools to complete
            results = loop.run_until_complete(asyncio.gather(*tasks))
            
            # Yield end events and add tool messages in the original order
            for events, tool_messages_list in results:
                # Filter out start events (already yielded), only yield end/error events
                for event in events:
                    if event.get("type") != "tool_call_start":
                        yield event
                # Add tool messages to the main messages list
                for tool_msg in tool_messages_list:
                    messages.append(tool_msg)
                    
        except Exception as e:
            logger.error(f"Error executing tools in parallel: {e}", exc_info=True)
            # Fallback to sequential execution
            logger.warning("Falling back to sequential tool execution")
            for tool_call_data in tool_calls:
                yield from self._execute_single_tool(tool_call_data, messages)

    def _should_stream_response(self, iteration: int, functions: List[Dict[str, Any]], has_tool_calls: bool) -> bool:
        """
        Determine if we should stream the final response.
        
        Args:
            iteration: Current iteration number
            functions: Available function definitions
            has_tool_calls: Whether tool calls were detected in this iteration
            
        Returns:
            True if should stream, False otherwise
        """
        if iteration > 1:
            # After tool execution, get final response with tool results
            logger.info(f"Streaming final response after tool execution (iteration {iteration})")
            return True
        elif iteration == 1 and not functions:
            # No functions available, stream normally
            logger.info("No functions available, streaming normally")
            return True
        elif iteration == 1 and functions and not has_tool_calls:
            # First iteration with functions but no tool calls detected or error occurred
            # Stream normally as fallback
            logger.info("First iteration with functions but no tool calls, streaming as fallback")
            return True
        return False

    def _stream_llm_response(self, messages: List[Dict[str, str]], system_prompt: str, disable_tools: bool = True) -> Generator[str, None, None]:
        """
        Stream LLM response chunks.
        
        Args:
            messages: Conversation messages
            system_prompt: System prompt for the LLM
            disable_tools: If True, explicitly disable tool calling (for final response after tool execution)
            
        Yields:
            Text chunks from LLM
        """
        stream_start_time = time.time()
        logger.info(f"Starting stream with {len(messages)} messages, disable_tools={disable_tools}")
        chunk_count = 0
        first_chunk_time = None
        
        # If we need to disable tools, we need to modify the payload
        if disable_tools:
            # Use the client directly to modify payload
            try:
                payload_start = time.time()
                client = self.llm_client._get_client()
                system_msg = {"role": "system", "content": system_prompt or ""}
                all_messages = [system_msg] + messages
                
                payload = client._normalize_payload(all_messages, model=client.model)
                # Explicitly disable function calling
                payload["function_call"] = "none"
                # Remove functions if present
                if "functions" in payload:
                    del payload["functions"]
                payload_time = time.time() - payload_start
                logger.info(f"[PERF] Stream payload preparation took {payload_time:.3f}s")
                
                # Make streaming request directly
                request_start = time.time()
                for chunk in client._make_stream_request("chat/completions", payload):
                    if first_chunk_time is None:
                        first_chunk_time = time.time() - request_start
                        logger.info(f"[PERF] First chunk received after {first_chunk_time:.3f}s (TTFB)")
                    chunk_count += 1
                    yield chunk
                request_time = time.time() - request_start
                logger.info(f"[PERF] Stream request took {request_time:.3f}s, received {chunk_count} chunks")
            except Exception as e:
                logger.error(f"Error in streaming with disabled tools: {e}", exc_info=True)
                # Fallback to normal streaming
                request_start = time.time()
                for chunk in self.llm_client.chat_stream(messages, system_prompt=system_prompt):
                    if first_chunk_time is None:
                        first_chunk_time = time.time() - request_start
                    chunk_count += 1
                    yield chunk
                request_time = time.time() - request_start
                logger.info(f"[PERF] Stream request (fallback) took {request_time:.3f}s, received {chunk_count} chunks")
        else:
            # Normal streaming
            request_start = time.time()
            for chunk in self.llm_client.chat_stream(messages, system_prompt=system_prompt):
                if first_chunk_time is None:
                    first_chunk_time = time.time() - request_start
                    logger.info(f"[PERF] First chunk received after {first_chunk_time:.3f}s (TTFB)")
                chunk_count += 1
                yield chunk
            request_time = time.time() - request_start
            logger.info(f"[PERF] Stream request took {request_time:.3f}s, received {chunk_count} chunks")
        
        total_time = time.time() - stream_start_time
        logger.info(f"[PERF] Total stream took {total_time:.3f}s, received {chunk_count} chunks")

    def chat_stream(self, request: ChatRequest) -> Generator[Dict[str, Any], None, None]:
        """
        Handle chat request with streaming response and tool calling support.
        
        Yields dictionaries with event information:
        - {"type": "chunk", "content": "..."} for text chunks
        - {"type": "tool_call_start", "tool": "...", "input": "..."} for tool call start
        - {"type": "tool_call_end", "tool": "...", "result": "..."} for tool call end
        - {"type": "tool_call_error", "tool": "...", "error": "..."} for tool call errors
        """
        chat_start_time = time.time()
        try:
            # Prepare messages from request
            prep_start = time.time()
            messages = self._prepare_messages(request)
            prep_time = time.time() - prep_start
            logger.info(f"[PERF] Message preparation took {prep_time:.3f}s")
            
            # Build system prompt
            prompt_start = time.time()
            system_prompt = self._build_agent_system_prompt()
            prompt_time = time.time() - prompt_start
            logger.info(f"[PERF] System prompt building took {prompt_time:.3f}s")

            # Handle empty conversation
            if not messages:
                yield {"type": "chunk", "content": "你好！我是您的旅行助手。我可以帮助您规划旅行、回答旅行相关问题、查找目的地信息等。请告诉我您需要什么帮助？"}
                return

            # Get function definitions for tool calling
            func_start = time.time()
            functions = self.mcp_registry.get_tool_function_definitions_sync()
            func_time = time.time() - func_start
            logger.info(f"[PERF] Function definitions loading took {func_time:.3f}s, found {len(functions)} functions")
            
            # Tool calling loop (max iterations)
            iteration = 0
            accumulated_content = ""
            
            while iteration < self.max_tool_iterations:
                iteration += 1
                iter_start_time = time.time()
                logger.info(f"[PERF] Starting iteration {iteration}/{self.max_tool_iterations}")
                
                try:
                    # Let LLM decide if tools are needed based on all tool results in messages
                    # LLM can see all tool results (role="tool" messages) and make intelligent decisions
                    has_tool_calls = False
                    tool_count = len([m for m in messages if m.get("role") == "tool"])
                    
                    # Always let LLM decide if more tools are needed (it can see all tool results)
                    if functions and iteration <= self.max_tool_iterations:
                        logger.info(f"Iteration {iteration}: Letting LLM decide if tools are needed (can see {tool_count} tool results from previous iterations)")
                        detection_result = self._detect_tool_calls(messages, system_prompt, functions)
                        
                        if detection_result:
                            content = detection_result["content"]
                            tool_calls = detection_result["tool_calls"]
                            
                            logger.info(f"Iteration {iteration}: Detection result - content length: {len(content) if content else 0}, tool_calls count: {len(tool_calls) if tool_calls else 0}")
                            
                            if tool_calls:
                                # Execute tool calls and yield events
                                logger.info(f"Iteration {iteration}: Executing {len(tool_calls)} tool calls")
                                yield from self._execute_tool_calls(tool_calls, content, messages)
                                has_tool_calls = True
                                # Continue to next iteration to let LLM decide again
                                continue
                            elif content and iteration == 1:
                                # First iteration with content but no tool calls - yield it directly
                                accumulated_content = content
                                yield {"type": "chunk", "content": content}
                                break
                            else:
                                # Later iterations: LLM decided to generate final response (no more tools)
                                logger.info(f"Iteration {iteration}: LLM decided to generate final response (no more tool calls)")
                        else:
                            logger.warning(f"Iteration {iteration}: Tool detection returned None, falling back to streaming")
                    
                    # Stream final response (after tool execution or if no tools needed)
                    if self._should_stream_response(iteration, functions, has_tool_calls):
                        # If we reach here, LLM decided not to call tools (or no tools detected)
                        # Disable tools for final response generation
                        disable_tools = True
                        # After max iterations, force final response
                        if iteration >= self.max_tool_iterations:
                            logger.info(f"Iteration {iteration}: Reached max iterations ({self.max_tool_iterations}), forcing final response")
                        else:
                            logger.info(f"Iteration {iteration}: LLM decided not to call tools, generating final response")
                        
                        chunk_count_in_iteration = 0
                        stream_start = time.time()
                        for chunk in self._stream_llm_response(messages, system_prompt, disable_tools=disable_tools):
                            accumulated_content += chunk
                            chunk_count_in_iteration += 1
                            yield {"type": "chunk", "content": chunk}
                        stream_time = time.time() - stream_start
                        logger.info(f"[PERF] Iteration {iteration} streaming took {stream_time:.3f}s, received {chunk_count_in_iteration} chunks")
                        
                        # If we received 0 chunks after tool execution, stop immediately
                        # This prevents infinite loops when LLM fails to generate response
                        if iteration > 1 and chunk_count_in_iteration == 0:
                            logger.warning(f"Iteration {iteration}: Received 0 chunks after tool execution. Stopping to prevent infinite loop.")
                            if not accumulated_content:
                                # Check if tools were used but didn't find useful information
                                tools_used_but_no_info = self._check_tools_used_but_no_info(messages)
                                if tools_used_but_no_info:
                                    yield {"type": "chunk", "content": "很抱歉，我尝试了多种方法查找相关信息，但未能找到您问题的答案。建议您联系Harry获取更具体的帮助。"}
                                else:
                                    yield {"type": "chunk", "content": "抱歉，处理请求时遇到问题，请重试。"}
                            break
                        
                        # If we got content and tools are disabled, we're done
                        if chunk_count_in_iteration > 0 and disable_tools:
                            logger.info(f"Iteration {iteration}: Got {chunk_count_in_iteration} chunks with tools disabled, completing")
                            # Check if tools were used but didn't find useful information, and suggest contacting Harry
                            if iteration > 1:
                                tools_used_but_no_info = self._check_tools_used_but_no_info(messages)
                                if tools_used_but_no_info and not self._response_suggests_contact_harry(accumulated_content):
                                    # Append suggestion to contact Harry if not already mentioned
                                    yield {"type": "chunk", "content": "\n\n如果您需要更具体的帮助，建议您联系Harry。"}
                            break
                    
                    iter_time = time.time() - iter_start_time
                    logger.info(f"[PERF] Iteration {iteration} total time: {iter_time:.3f}s")
                    
                    # Check if we're done
                    if accumulated_content:
                        logger.info(f"Completed with content (length: {len(accumulated_content)})")
                        # Check if tools were used but didn't find useful information
                        if iteration > 1:
                            tools_used_but_no_info = self._check_tools_used_but_no_info(messages)
                            if tools_used_but_no_info and not self._response_suggests_contact_harry(accumulated_content):
                                # Append suggestion to contact Harry if not already mentioned
                                yield {"type": "chunk", "content": "\n\n如果您需要更具体的帮助，建议您联系Harry。"}
                        break
                    elif iteration >= self.max_tool_iterations:
                        logger.warning(f"Reached max iterations ({self.max_tool_iterations}) without content")
                        if not accumulated_content:
                            # Check if tools were used but didn't find useful information
                            tools_used_but_no_info = self._check_tools_used_but_no_info(messages)
                            if tools_used_but_no_info:
                                yield {"type": "chunk", "content": "很抱歉，我尝试了多种方法查找相关信息，但未能找到您问题的答案。建议您联系Harry获取更具体的帮助。"}
                            else:
                                yield {"type": "chunk", "content": "抱歉，处理请求时遇到问题，请重试。"}
                        break
                        
                except LLMError as exc:
                    error_msg = format_error_message(exc, "Error processing request")
                    yield {"type": "chunk", "content": error_msg}
                    break
                except Exception as exc:
                    logger.error(f"Unexpected error during LLM streaming: {exc}", exc_info=True)
                    yield {"type": "chunk", "content": f"An unexpected error occurred: {str(exc)}"}
                    break
            
            if iteration >= self.max_tool_iterations:
                logger.warning(f"Reached maximum tool calling iterations ({self.max_tool_iterations})")
            
            total_time = time.time() - chat_start_time
            logger.info(f"[PERF] Total chat_stream took {total_time:.3f}s, completed {iteration} iterations")

        except Exception as exc:
            total_time = time.time() - chat_start_time
            logger.error(f"[PERF] chat_stream failed after {total_time:.3f}s: {exc}", exc_info=True)
            yield {"type": "chunk", "content": f"An error occurred while processing your request: {str(exc)}"}
