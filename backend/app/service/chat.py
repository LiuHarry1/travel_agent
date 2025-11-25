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

                    # Get LLM client
                    client = self.llm_client._get_client()
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

                    # Track tool call state
                    tool_calls_by_id: Dict[str, Dict[str, Any]] = {}
                    chunk_count = 0
                    first_chunk_time = None

                    # Stream and parse in real-time
                    request_start = time.time()
                    line_count = 0
                    stream_ended = False
                    async for line in self._stream_llm_response(client, payload):
                        line_count += 1
                        if first_chunk_time is None:
                            first_chunk_time = time.time() - request_start
                            logger.info(
                                f"[PERF] First chunk received after {first_chunk_time:.3f}s (TTFB)"
                            )

                        # Check for [DONE] signal
                        if line.strip() == "data: [DONE]":
                            stream_ended = True
                            logger.debug("Received [DONE] signal from stream")
                            break

                        # Parse chunk to extract content and tool call info
                        content_chunk, tool_call_updates = self._parse_stream_chunk(
                            line, tool_calls_by_id
                        )

                        # Immediately detect tool call in first relevant chunk
                        if tool_call_updates and not tool_call_detected:
                            tool_call_detected = True
                            logger.info(
                                f"🔧 Tool call detected in line {line_count}, "
                                "immediately stopping text streaming"
                            )
                            # Log tool call details for debugging
                            for call_id, call_data in tool_calls_by_id.items():
                                func_info = call_data.get("function", {})
                                name = func_info.get("name", "")
                                args = func_info.get("arguments", "")
                                logger.info(
                                    f"  Tool call '{call_id}': name='{name}', "
                                    f"args_length={len(args)}, args_preview='{args[:100]}'"
                                )

                        # Only yield text content if NO tool call has been detected
                        if content_chunk and not tool_call_detected:
                            accumulated_text += content_chunk
                            accumulated_content += content_chunk
                            chunk_count += 1
                            yield {"type": "chunk", "content": content_chunk}
                        elif content_chunk and tool_call_detected:
                            # Skip text content when tool call is detected
                            logger.debug(
                                f"Skipping text content chunk (tool call detected): "
                                f"{content_chunk[:50]}"
                            )

                        # Check if tool calls are complete (must have valid JSON arguments)
                        # But only break if we've seen the complete JSON and stream is about to end
                        # We want to collect all arguments before breaking
                        if tool_call_detected and tool_calls_by_id:
                            complete_tool_calls = self._get_complete_tool_calls(
                                tool_calls_by_id
                            )
                            if complete_tool_calls:
                                # Double-check: make sure all tool calls are complete
                                all_complete = True
                                for call in complete_tool_calls:
                                    args = call.get("function", {}).get("arguments", "")
                                    if args:
                                        try:
                                            json.loads(args)
                                        except json.JSONDecodeError:
                                            all_complete = False
                                            break
                                
                                if all_complete:
                                    logger.info(
                                        f"✅ Detected {len(complete_tool_calls)} complete tool calls "
                                        "with valid arguments, will stop after current chunk"
                                    )
                                    # Don't break immediately - wait for stream to naturally end
                                    # This ensures we get all chunks with tool call data
                                    tool_call_data = {
                                        "tool_calls": complete_tool_calls
                                    }

                    stream_time = time.time() - request_start
                    logger.info(
                        f"[PERF] Streaming took {stream_time:.3f}s, "
                        f"received {line_count} lines, {chunk_count} content chunks, "
                        f"tool_call_detected: {tool_call_detected}, "
                        f"tool_calls_by_id count: {len(tool_calls_by_id)}"
                    )

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
                                async for line in self._stream_llm_response(
                                    client, payload_no_tools
                                ):
                                    content = self._extract_content_from_line(line)
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

    async def _stream_llm_response(
        self, client, payload: Dict[str, Any]
    ) -> AsyncGenerator[str, None]:
        """Stream LLM response lines (SSE format)."""
        try:
            async_client = client._get_async_client()
            base_url = client._get_base_url()
            url = f"{base_url}/chat/completions"

            headers = {"Content-Type": "application/json"}
            if client.api_key:
                headers["Authorization"] = f"Bearer {client.api_key}"

            # Convert functions to tools if using OpenAIClient
            if isinstance(client, OpenAIClient):
                request_payload = client._convert_functions_to_tools(payload.copy())
            else:
                request_payload = payload.copy()

            request_payload["stream"] = True

            async with async_client.stream("POST", url, json=request_payload, headers=headers) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if line:
                        yield line
        except Exception as e:
            logger.error(f"Error in streaming: {e}", exc_info=True)
            raise

    def _parse_stream_chunk(
        self, line: str, tool_calls_by_id: Dict[str, Dict[str, Any]]
    ) -> Tuple[str, List[Dict[str, Any]]]:
        """
        Parse SSE line to extract content and tool call updates.
        
        Returns:
            Tuple of (content_chunk, tool_call_updates)
        """
        if not line.startswith("data: "):
            return ("", [])

        data_str = line[6:].strip()
        if data_str == "[DONE]":
            return ("", [])

        if not data_str:
            return ("", [])

        try:
            chunk_data = json.loads(data_str)
        except json.JSONDecodeError:
            return ("", [])

        if "choices" not in chunk_data or not chunk_data["choices"]:
            return ("", [])

        delta = chunk_data["choices"][0].get("delta", {})
        content = delta.get("content") or delta.get("text", "")

        # Extract tool call information from delta
        tool_call_updates = []

        # Check for function_call (Qwen/DashScope format)
        if "function_call" in delta:
            func_call = delta["function_call"]
            call_id = func_call.get("id") or func_call.get("index", "default")

            if call_id not in tool_calls_by_id:
                tool_calls_by_id[call_id] = {
                    "id": call_id,
                    "type": "function",
                    "function": {"name": "", "arguments": ""},
                }

            if "name" in func_call and func_call["name"]:
                tool_calls_by_id[call_id]["function"]["name"] = func_call["name"]
            if "arguments" in func_call:
                args_value = func_call.get("arguments")
                if args_value is not None:
                    # Ensure we're working with a string
                    tool_calls_by_id[call_id]["function"]["arguments"] += str(args_value)

            tool_call_updates.append(tool_calls_by_id[call_id])

        # Check for tool_calls (OpenAI format)
        # Similar to backend_new: use index as primary key for matching
        # This is more reliable than call_id because index is always present
        if "tool_calls" in delta:
            for tool_call_delta in delta["tool_calls"]:
                call_id = tool_call_delta.get("id")  # May be None/empty for continuation chunks
                index = tool_call_delta.get("index", 0)

                # CRITICAL: Use index as primary key for matching (like backend_new uses single variable)
                # Index is always present and stable across chunks, unlike call_id which may be empty
                matched_call_id = None
                
                # Priority 1: Try to find existing tool call by index (most reliable)
                for existing_id, existing_call in tool_calls_by_id.items():
                    if existing_call.get("index") == index:
                        matched_call_id = existing_id
                        logger.debug(
                            f"Matched tool call by index {index}: using call_id '{matched_call_id}'"
                        )
                        break
                
                # Priority 2: If found by index but call_id is provided and different, update it
                if matched_call_id and call_id and call_id != matched_call_id:
                    # Update the stored call_id if we have a new one
                    tool_calls_by_id[matched_call_id]["id"] = call_id
                    logger.debug(
                        f"Updated call_id for index {index}: '{matched_call_id}' -> '{call_id}'"
                    )
                    # Optionally rename the key if we want to use the new call_id
                    # For now, keep using the existing key to avoid complexity
                
                # Priority 3: If no match by index, but we have call_id, try to find by call_id
                if not matched_call_id and call_id:
                    if call_id in tool_calls_by_id:
                        matched_call_id = call_id
                        logger.debug(f"Matched tool call by call_id: '{call_id}'")
                    else:
                        # New tool call with call_id
                        matched_call_id = call_id
                
                # Priority 4: If still no match, create new entry (use index-based ID)
                if not matched_call_id:
                    # Use call_id if available, otherwise generate index-based ID
                    matched_call_id = call_id or f"call_index_{index}"
                    logger.debug(
                        f"Creating new tool call entry: '{matched_call_id}' (index={index})"
                    )
                
                # Create entry if it doesn't exist
                if matched_call_id not in tool_calls_by_id:
                    tool_calls_by_id[matched_call_id] = {
                        "id": call_id or matched_call_id,  # Store original call_id if available
                        "type": "function",
                        "function": {"name": "", "arguments": ""},
                        "index": index,
                    }
                
                # Update the matched tool call (accumulate like backend_new)
                if "function" in tool_call_delta:
                    func_delta = tool_call_delta["function"]
                    if "name" in func_delta and func_delta["name"]:
                        tool_calls_by_id[matched_call_id]["function"]["name"] = func_delta[
                            "name"
                        ]
                    if "arguments" in func_delta:
                        args_value = func_delta.get("arguments")
                        if args_value is not None:
                            # Accumulate arguments (like backend_new does)
                            tool_calls_by_id[matched_call_id]["function"]["arguments"] += str(args_value)

                tool_call_updates.append(tool_calls_by_id[matched_call_id])

        return (content, tool_call_updates)

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

    def _extract_content_from_line(self, line: str) -> str:
        """Extract content from SSE line."""
        if not line.startswith("data: "):
            return ""

        data_str = line[6:].strip()
        if data_str == "[DONE]" or not data_str:
            return ""

        try:
            chunk_data = json.loads(data_str)
            if "choices" not in chunk_data or not chunk_data["choices"]:
                return ""
            delta = chunk_data["choices"][0].get("delta", {})
            return delta.get("content") or delta.get("text", "") or ""
        except json.JSONDecodeError:
            return ""
