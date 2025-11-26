"""Chat service for conversational travel agent with MCP tool calling."""
from __future__ import annotations

import json
import logging
import time
from typing import Any, AsyncGenerator, Dict, List, Optional, Tuple

from ..config import get_config
from ..llm import LLMClient, LLMError
from ..llm.openai import OpenAIClient
from ..mcp_tools import MCPManager
from ..models import ChatRequest
from ..utils.exceptions import format_error_message
from .message_processing import MessageProcessingService
from .tool_execution import ToolExecutionService
from .tool_result_formatter import (
    check_tools_used_but_no_info,
    format_tool_result_for_llm,
    response_suggests_contact_harry,
)

logger = logging.getLogger(__name__)


class ChatService:
    """Service for conversational travel agent with MCP tool calling."""

    def __init__(
        self,
        llm_client: Optional[LLMClient] = None,
        mcp_registry: Optional[MCPManager] = None,
    ):
        """Initialize chat service."""
        self.llm_client = llm_client or LLMClient()
        self.mcp_registry = mcp_registry or MCPManager()
        self.max_tool_iterations = 4

        # Initialize sub-services
        self.message_processor = MessageProcessingService(get_config)
        self.message_processor.set_mcp_registry(self.mcp_registry)
        self.tool_executor = ToolExecutionService(
            self.mcp_registry, format_tool_result_for_llm
        )

    async def chat_stream(
        self, request: ChatRequest
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Handle chat request with streaming response and tool calling support.
        
        Based on backend_new logic: stream from start, detect tool calls in real-time.
        
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
            messages = self.message_processor.prepare_messages(request)
            prep_time = time.time() - prep_start
            logger.info(f"[PERF] Message preparation took {prep_time:.3f}s")

            # Build system prompt
            prompt_start = time.time()
            system_prompt = self.message_processor.build_agent_system_prompt()
            prompt_time = time.time() - prompt_start
            logger.info(f"[PERF] System prompt building took {prompt_time:.3f}s")

            # Handle empty conversation
            if not messages:
                yield {
                    "type": "chunk",
                    "content": "你好！我是您的旅行助手。我可以帮助您规划旅行、回答旅行相关问题、查找目的地信息等。请告诉我您需要什么帮助？",
                }
                return

            # Get function definitions for tool calling (async)
            func_start = time.time()
            functions = await self.mcp_registry.get_tool_function_definitions()
            func_time = time.time() - func_start
            logger.info(
                f"[PERF] Function definitions loading took {func_time:.3f}s, "
                f"found {len(functions)} functions"
            )

            # Main chat loop - similar to backend_new agent.py
            iteration = 0
            accumulated_content = ""

            while iteration < self.max_tool_iterations:
                iteration += 1
                iter_start_time = time.time()
                logger.info(
                    f"\n{'='*60}\nIteration {iteration}/{self.max_tool_iterations}\n{'='*60}"
                )

                try:
                    # Step 1: Stream LLM response with real-time tool call detection
                    tool_call_detected = False
                    tool_call_data: Optional[Dict[str, Any]] = None
                    accumulated_text = ""

                    # Get LLM client early to ensure connection pool is ready
                    # This helps reduce latency by having the client and connection pool initialized
                    client = self.llm_client._get_client()
                    
                    # Pre-initialize OpenAI client and HTTP client if using OpenAI SDK
                    # This ensures connection pool is ready before making the request
                    if isinstance(client, OpenAIClient):
                        # Ensure HTTP client and OpenAI client are initialized
                        _ = client._get_http_client()  # Initialize connection pool
                        _ = client._get_openai_client()  # Initialize OpenAI client
                    
                    system_msg = {"role": "system", "content": system_prompt or ""}
                    all_messages = [system_msg] + messages

                    # Prepare payload
                    payload = client._normalize_payload(all_messages, model=client.model)
                    payload["stream"] = True

                    # Add tools if available
                    if functions:
                        # Convert functions to tools format for OpenAI-compatible API
                        if isinstance(client, OpenAIClient):
                            tools = []
                            for func in functions:
                                tools.append({
                                    "type": "function",
                                    "function": func
                                })
                            payload["tools"] = tools
                            payload["tool_choice"] = "auto"
                        else:
                            # Legacy format for other providers
                            payload["functions"] = functions
                            payload["function_call"] = "auto"

                    logger.info(
                        f"Starting stream request with {len(functions)} functions available"
                    )

                    # Track tool call state - similar to backend_new agent.py
                    current_tool_call: Optional[Dict[str, Any]] = None
                    tool_call_id: Optional[str] = None
                    tool_call_name: Optional[str] = None
                    tool_call_args_buffer = ""
                    tool_calls_by_id: Dict[str, Dict[str, Any]] = {}
                    chunk_count = 0
                    first_chunk_time = None

                    # Stream and parse in real-time using SDK directly
                    request_start = time.time()
                    chunk_index = 0
                    
                    # Use SDK's streaming method directly (no httpx)
                    async for chunk in client._make_stream_request("chat/completions", payload):
                        chunk_index += 1
                        if first_chunk_time is None:
                            first_chunk_time = time.time() - request_start
                            logger.info(
                                f"[PERF] First chunk received after {first_chunk_time:.3f}s (TTFB)"
                            )

                        # Extract content and tool calls from SDK chunk object
                        # Similar to backend_new agent.py logic
                        if chunk.choices and len(chunk.choices) > 0:
                            delta = chunk.choices[0].delta
                            
                            # Check for tool_calls (OpenAI format)
                            if hasattr(delta, 'tool_calls') and delta.tool_calls:
                                tool_call_detected = True
                                
                                for tool_call_delta in delta.tool_calls:
                                    # Initialize tool call structure
                                    if current_tool_call is None:
                                        tool_call_id = getattr(tool_call_delta, 'id', None)
                                        current_tool_call = {
                                            "id": tool_call_id or f"call_{iteration}_{chunk_index}",
                                            "type": "function",
                                            "function": {"name": "", "arguments": ""}
                                        }
                                    
                                    # Accumulate tool call information
                                    func_delta = getattr(tool_call_delta, 'function', None)
                                    if func_delta:
                                        func_name = getattr(func_delta, 'name', None)
                                        if func_name:
                                            tool_call_name = func_name
                                            current_tool_call["function"]["name"] = tool_call_name
                                        
                                        func_args = getattr(func_delta, 'arguments', None)
                                        if func_args:
                                            tool_call_args_buffer += func_args
                                            current_tool_call["function"]["arguments"] += func_args
                                    
                                    # Store in tool_calls_by_id for compatibility
                                    call_id = current_tool_call["id"]
                                    if call_id not in tool_calls_by_id:
                                        tool_calls_by_id[call_id] = current_tool_call.copy()
                                    else:
                                        # Update existing entry
                                        existing = tool_calls_by_id[call_id]
                                        if tool_call_name:
                                            existing["function"]["name"] = tool_call_name
                                        if func_args:
                                            existing["function"]["arguments"] += func_args
                            
                            # Check for regular text content
                            content = getattr(delta, 'content', None)
                            if content:
                                if not tool_call_detected:
                                    # Only yield text if no tool call detected
                                    accumulated_text += content
                                    accumulated_content += content
                                    chunk_count += 1
                                    yield {"type": "chunk", "content": content}
                                else:
                                    # Skip text content when tool call is detected
                                    logger.debug(
                                        f"Skipping text content chunk (tool call detected): "
                                        f"{content[:50]}"
                                    )

                            # Log tool call detection
                            if tool_call_detected and current_tool_call and chunk_index == 1:
                                logger.info(
                                    f"🔧 Tool call detected in first chunk, "
                                    "stopping text streaming"
                                )
                                name = current_tool_call["function"].get("name", "")
                                args = current_tool_call["function"].get("arguments", "")
                                logger.info(
                                    f"  Tool call: name='{name}', "
                                    f"args_length={len(args)}, args_preview='{args[:100]}'"
                                )

                    # After stream ends, process tool calls (similar to backend_new)
                    stream_time = time.time() - request_start
                    logger.info(
                        f"[PERF] Streaming took {stream_time:.3f}s, "
                        f"received {chunk_index} chunks, {chunk_count} content chunks, "
                        f"tool_call_detected: {tool_call_detected}"
                    )
                    
                    # Process tool calls after stream ends (similar to backend_new agent.py)
                    if tool_call_detected and current_tool_call:
                        # Validate and parse tool call arguments
                        tool_name = tool_call_name or current_tool_call["function"].get("name", "")
                        
                        if not tool_name:
                            logger.warning("Tool call detected but no name found")
                            yield {
                                "type": "tool_call_error",
                                "tool": "unknown",
                                "error": "工具调用检测到但名称未完成"
                            }
                            continue
                        
                        # Validate arguments JSON
                        if not tool_call_args_buffer:
                            args = {}
                            logger.info(f"🔧 Tool call detected: {tool_name} (no arguments)")
                            tool_call_data = {
                                "id": current_tool_call["id"],
                                "name": tool_name,
                                "args": args,
                                "raw": current_tool_call
                            }
                        else:
                            try:
                                args = json.loads(tool_call_args_buffer)
                                logger.info(f"🔧 Tool call detected: {tool_name} with valid args: {args}")
                                tool_call_data = {
                                    "id": current_tool_call["id"],
                                    "name": tool_name,
                                    "args": args,
                                    "raw": current_tool_call
                                }
                            except json.JSONDecodeError as e:
                                logger.error(
                                    f"❌ Failed to parse tool call arguments for '{tool_name}': "
                                    f"'{tool_call_args_buffer[:200]}'. Error: {e}"
                                )
                                yield {
                                    "type": "tool_call_error",
                                    "tool": tool_name,
                                    "error": f"工具参数解析失败：JSON格式不完整或无效。原始参数: {tool_call_args_buffer[:100]}"
                                }
                                tool_call_data = None
                        
                        if tool_call_data:
                            # Convert to format expected by existing code
                            tool_call_data = {
                                "tool_calls": [{
                                    "id": tool_call_data["id"],
                                    "type": "function",
                                    "function": {
                                        "name": tool_call_data["name"],
                                        "arguments": json.dumps(tool_call_data["args"], ensure_ascii=False)
                                    }
                                }]
                            }

                    # If we detected tool calls but didn't complete them, try to get complete ones now
                    if tool_call_detected and tool_calls_by_id and not tool_call_data:
                        # Log current state of tool calls
                        logger.info(
                            f"Stream ended with tool calls detected but not complete. "
                            f"Checking {len(tool_calls_by_id)} tool call(s)..."
                        )
                        for call_id, call_data in tool_calls_by_id.items():
                            func_info = call_data.get("function", {})
                            name = func_info.get("name", "")
                            args = func_info.get("arguments", "")
                            logger.info(
                                f"  Tool call '{call_id}': name='{name}', "
                                f"args_length={len(args)}, args='{args[:200]}'"
                            )
                            # Try to parse arguments to check if valid
                            if args:
                                try:
                                    json.loads(args)
                                    logger.info(f"    ✅ Arguments are valid JSON")
                                except json.JSONDecodeError as e:
                                    logger.warning(
                                        f"    ❌ Arguments are NOT valid JSON: {str(e)[:100]}"
                                    )
                        
                        complete_tool_calls = self._get_complete_tool_calls(
                            tool_calls_by_id
                        )
                        if complete_tool_calls:
                            logger.info(
                                f"✅ Found {len(complete_tool_calls)} complete tool calls "
                                "after stream ended"
                            )
                            tool_call_data = {"tool_calls": complete_tool_calls}
                        else:
                            # Even if arguments are incomplete, if we have a name, we should try to execute
                            # This handles cases where the LLM provider doesn't send complete JSON
                            logger.warning(
                                "No complete tool calls found, but tool calls were detected. "
                                "Attempting to use incomplete tool calls..."
                            )
                            # Merge incomplete tool calls that belong together
                            # (e.g., when parameters are split across chunks with empty IDs)
                            merged_calls = {}
                            for call_id, call_data in tool_calls_by_id.items():
                                func_info = call_data.get("function", {})
                                name = func_info.get("name", "")
                                args = func_info.get("arguments", "")
                                
                                if name:
                                    # Try to merge tool calls with the same name
                                    # (parameters might be split across multiple entries)
                                    if name not in merged_calls:
                                        merged_calls[name] = call_data
                                    else:
                                        # Merge arguments from this call into the merged one
                                        existing_args = merged_calls[name].get("function", {}).get("arguments", "")
                                        merged_calls[name]["function"]["arguments"] = existing_args + args
                                        logger.debug(
                                            f"Merged tool call '{name}': combined arguments "
                                            f"(existing={len(existing_args)}, added={len(args)})"
                                        )
                            
                            if merged_calls:
                                incomplete_calls = list(merged_calls.values())
                                logger.info(
                                    f"Using {len(incomplete_calls)} incomplete tool call(s) "
                                    "(merged from multiple entries, will attempt execution, errors will be handled)"
                                )
                                tool_call_data = {"tool_calls": incomplete_calls}

                    # Step 2: Handle tool calls or text response
                    if tool_call_data and tool_call_data.get("tool_calls"):
                        # Execute tool calls
                        tool_calls = tool_call_data["tool_calls"]
                        logger.info(
                            f"Iteration {iteration}: Executing {len(tool_calls)} tool calls"
                        )

                        async for event in self.tool_executor.execute_tool_calls(
                            tool_calls, "", messages
                        ):
                            yield event

                        # Continue to next iteration to get LLM's response
                        continue

                    elif accumulated_text:
                        # Normal text response - we're done
                        logger.info(
                            f"✅ Normal response (length: {len(accumulated_text)})"
                        )
                        # Check if tools were used but didn't find useful information
                        if iteration > 1:
                            tools_used_but_no_info = check_tools_used_but_no_info(
                                messages
                            )
                            if tools_used_but_no_info and not response_suggests_contact_harry(
                                accumulated_content
                            ):
                                yield {
                                    "type": "chunk",
                                    "content": "\n\n如果您需要更具体的帮助，建议您联系Harry。",
                                }
                        break  # Conversation ended

                    else:
                        # No tool call and no text - might indicate a problem
                        logger.warning(
                            f"Iteration {iteration}: No tool call and no text content received"
                        )
                        if iteration == 1:
                            # Try fallback: stream without tools
                            logger.info(
                                f"Iteration {iteration}: Attempting fallback streaming "
                                "without tool detection"
                            )
                            try:
                                payload_no_tools = client._normalize_payload(
                                    all_messages, model=client.model
                                )
                                payload_no_tools["stream"] = True
                                if "tools" in payload_no_tools:
                                    del payload_no_tools["tools"]
                                if "functions" in payload_no_tools:
                                    del payload_no_tools["functions"]

                                chunk_count = 0
                                # Use SDK streaming directly for fallback
                                async for chunk in client._make_stream_request("chat/completions", payload_no_tools):
                                    if chunk.choices and len(chunk.choices) > 0:
                                        delta = chunk.choices[0].delta
                                        content = getattr(delta, 'content', None)
                                        if content:
                                            accumulated_text += content
                                            accumulated_content += content
                                            chunk_count += 1
                                            yield {"type": "chunk", "content": content}

                                if chunk_count > 0:
                                    logger.info(
                                        f"Fallback streaming succeeded: received {chunk_count} chunks"
                                    )
                                    break
                                else:
                                    logger.error(
                                        "Fallback streaming also returned 0 chunks"
                                    )
                                    yield {
                                        "type": "chunk",
                                        "content": "抱歉，无法获取模型回复。请检查网络连接或稍后重试。",
                                    }
                                    break
                            except Exception as fallback_error:
                                logger.error(
                                    f"Fallback streaming failed: {fallback_error}",
                                    exc_info=True,
                                )
                                yield {
                                    "type": "chunk",
                                    "content": f"处理请求时出错: {str(fallback_error)}",
                                }
                                break
                        else:
                            # Stop to avoid infinite loop
                            logger.error(
                                f"Iteration {iteration}: No content received, stopping"
                            )
                            yield {
                                "type": "chunk",
                                "content": "抱歉，处理请求时遇到问题。请重试。",
                            }
                            break

                    iter_time = time.time() - iter_start_time
                    logger.info(f"[PERF] Iteration {iteration} total time: {iter_time:.3f}s")

                except LLMError as exc:
                    error_msg = format_error_message(exc, "Error processing request")
                    yield {"type": "chunk", "content": error_msg}
                    break
                except Exception as exc:
                    logger.error(
                        f"Unexpected error during LLM streaming: {exc}", exc_info=True
                    )
                    yield {
                        "type": "chunk",
                        "content": f"An unexpected error occurred: {str(exc)}",
                    }
                    break

            if iteration >= self.max_tool_iterations:
                logger.warning(
                    f"Reached maximum tool calling iterations ({self.max_tool_iterations})"
                )

            total_time = time.time() - chat_start_time
            logger.info(
                f"[PERF] Total chat_stream took {total_time:.3f}s, "
                f"completed {iteration} iterations"
            )

        except Exception as exc:
            total_time = time.time() - chat_start_time
            logger.error(
                f"[PERF] chat_stream failed after {total_time:.3f}s: {exc}", exc_info=True
            )
            yield {
                "type": "chunk",
                "content": f"An error occurred while processing your request: {str(exc)}",
            }


    def _get_complete_tool_calls(
        self, tool_calls_by_id: Dict[str, Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Get complete tool calls (those with both name and valid JSON arguments).
        
        IMPORTANT: We validate that arguments are valid JSON before considering
        a tool call complete. This prevents parsing errors when arguments are
        still being streamed and incomplete.
        """
        complete_calls = []
        for call_id, call_data in tool_calls_by_id.items():
            func_info = call_data.get("function", {})
            name = func_info.get("name", "")
            arguments = func_info.get("arguments", "")

            # Must have a name
            if not name:
                continue

            # Validate arguments: must be valid JSON (or empty string for providers that don't use args)
            if arguments:
                try:
                    # Try to parse as JSON to ensure it's complete
                    json.loads(arguments)
                    # If parsing succeeds, arguments are complete
                    complete_calls.append(call_data)
                except json.JSONDecodeError:
                    # Arguments exist but are incomplete JSON - not ready yet
                    logger.debug(
                        f"Tool call '{name}' has incomplete arguments "
                        f"(not valid JSON yet): {arguments[:100]}"
                    )
                    continue
            else:
                # Empty arguments - some providers may allow this
                # Consider it complete if name exists
                complete_calls.append(call_data)

        return complete_calls if complete_calls else []

