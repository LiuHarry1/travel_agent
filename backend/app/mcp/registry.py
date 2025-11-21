"""MCP tool registry and execution."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from .client import MCPClient
from .config import load_mcp_config, MCPToolConfig

logger = logging.getLogger(__name__)


@dataclass
class ToolCall:
    """Represents a tool call request."""
    name: str
    arguments: Dict[str, Any]
    id: Optional[str] = None


@dataclass
class ToolResult:
    """Represents the result of a tool call."""
    tool_name: str
    success: bool
    result: Any
    error: Optional[str] = None


class MCPToolRegistry:
    """Registry for MCP tools that loads tool definitions from MCP servers."""
    
    def __init__(self, config_path: Optional[str] = None):
        """Initialize registry with tools from MCP servers."""
        self.tools: Dict[str, Dict[str, Any]] = {}
        self._tool_implementations: Dict[str, Any] = {}
        self._tool_to_server: Dict[str, str] = {}  # Map tool name to server name
        self._load_tools_from_servers(config_path)
    
    def _load_tools_from_servers(self, config_path: Optional[str] = None) -> None:
        """Load tool definitions from MCP servers (both internal Python modules and external servers)."""
        config = load_mcp_config(config_path)
        servers = config.get("mcpServers", {})
        
        logger.info(f"[MCPToolRegistry] Loading tools from {len(servers)} MCP servers")
        
        # Map server names to their modules (internal Python servers)
        server_modules = {
            "faq": ("app.mcp.faq.server", "faq"),
            "travel-doc-retriever": ("app.mcp.travel_doc_retriever.server", "retriever")
        }
        
        # Separate internal and external servers
        self._mcp_clients: Dict[str, MCPClient] = {}
        
        # Load tools from each server
        for server_name, server_config in servers.items():
            try:
                command = server_config.get("command", "")
                args = server_config.get("args", [])
                env = server_config.get("env", {})
                
                # Check if it's an internal Python server (command is "python" and args start with "-m")
                is_internal = command == "python" and args and len(args) >= 2 and args[0] == "-m"
                
                if is_internal:
                    # Load from internal Python module
                    module_path = args[1]
                    if server_name not in server_modules:
                        # Try to get from args
                        if not module_path.startswith("app.mcp."):
                            logger.warning(f"[MCPToolRegistry] Skipping internal server {server_name} (not in app.mcp)")
                            continue
                    
                    # Import the server module and get tools
                    import importlib
                    module = importlib.import_module(module_path)
                    
                    # Get the app (Server instance) from the module
                    if hasattr(module, "app"):
                        # Call list_tools handler directly
                        import asyncio
                        import inspect
                        try:
                            loop = asyncio.get_event_loop()
                        except RuntimeError:
                            loop = asyncio.new_event_loop()
                            asyncio.set_event_loop(loop)
                        
                        # Find the list_tools function in the module
                        list_tools_func = None
                        for name, obj in inspect.getmembers(module):
                            if (inspect.isfunction(obj) or inspect.iscoroutinefunction(obj)) and name == "list_tools":
                                list_tools_func = obj
                                break
                        
                        if list_tools_func:
                            # Call the async function
                            if inspect.iscoroutinefunction(list_tools_func):
                                tools = loop.run_until_complete(list_tools_func())
                            else:
                                tools = list_tools_func()
                        else:
                            logger.warning(f"[MCPToolRegistry] Could not find list_tools function in {module_path}")
                            continue
                        
                        for tool in tools:
                            tool_name = tool.name if hasattr(tool, 'name') else tool.get("name", "")
                            if tool_name:
                                # Convert Tool object to dict
                                tool_dict = {
                                    "name": tool_name,
                                    "description": tool.description if hasattr(tool, 'description') else tool.get("description", ""),
                                    "inputSchema": tool.inputSchema if hasattr(tool, 'inputSchema') else tool.get("inputSchema", {})
                                }
                                self.tools[tool_name] = tool_dict
                                self._tool_to_server[tool_name] = server_name
                                
                                # Also load the tool implementation for direct calling
                                if server_name == "faq":
                                    from .faq.tool import FAQTool
                                    self._tool_implementations[tool_name] = FAQTool()
                                elif server_name == "travel-doc-retriever":
                                    from .travel_doc_retriever.tool import RetrieverTool
                                    self._tool_implementations[tool_name] = RetrieverTool()
                                
                                logger.info(f"[MCPToolRegistry] Loaded tool '{tool_name}' from internal server '{server_name}'")
                
                else:
                    # External MCP server - use MCP client to connect
                    logger.info(f"[MCPToolRegistry] Setting up MCP client for external server: {server_name}")
                    env = server_config.get("env", {})
                    client = MCPClient(command, args, env=env)
                    # Store client for later initialization
                    self._mcp_clients[server_name] = client
                    # Note: We'll initialize and load tools lazily when needed
                    logger.info(f"[MCPToolRegistry] MCP client created for external server '{server_name}' (will load tools on first use)")
                
            except Exception as e:
                logger.error(f"[MCPToolRegistry] Failed to load tools from server {server_name}: {e}", exc_info=True)
        
        logger.info(f"[MCPToolRegistry] Total tools loaded: {len(self.tools)} (internal: {len(self.tools)}, external clients: {len(self._mcp_clients)})")
    
    def list_tools(self) -> List[MCPToolConfig]:
        """List all registered tools (returns MCPToolConfig for backward compatibility)."""
        result = []
        for tool in self.tools.values():
            result.append(MCPToolConfig(
                name=tool.get("name", ""),
                tool_type="",  # Not needed when using MCP servers
                description=tool.get("description", ""),
                inputSchema=tool.get("inputSchema", {})
            ))
        return result
    
    def list_tools_dict(self) -> List[Dict[str, Any]]:
        """List all registered tools as dictionaries."""
        return list(self.tools.values())
    
    async def _ensure_external_tools_loaded(self) -> None:
        """Lazily load tools from external MCP servers."""
        for server_name, client in self._mcp_clients.items():
            try:
                if not client._initialized:
                    await client.initialize()
                    
                    # Get tools from this server
                    tools = await client.list_tools()
                    for tool in tools:
                        tool_name = tool.get("name", "")
                        if tool_name and tool_name not in self.tools:
                            self.tools[tool_name] = tool
                            self._tool_to_server[tool_name] = server_name
                            logger.info(f"[MCPToolRegistry] Loaded tool '{tool_name}' from external server '{server_name}'")
                
            except Exception as e:
                logger.error(f"[MCPToolRegistry] Failed to load tools from external server {server_name}: {e}", exc_info=True)
    
    async def call_tool(self, tool_call: ToolCall) -> ToolResult:
        """
        Execute a tool call using direct tool implementation or MCP client.
        
        Args:
            tool_call: Tool call request
            
        Returns:
            ToolResult with execution result
        """
        logger.info(f"[MCPToolRegistry] Calling tool: {tool_call.name} with arguments: {tool_call.arguments}")
        
        # Ensure external tools are loaded
        await self._ensure_external_tools_loaded()
        
        # Check if it's an internal tool (has direct implementation)
        tool_impl = self._tool_implementations.get(tool_call.name)
        
        if tool_impl:
            # Internal tool - call directly
            try:
                if hasattr(tool_impl, "execute"):
                    result = await tool_impl.execute(tool_call.arguments)
                    server_name = self._tool_to_server.get(tool_call.name, "unknown")
                    logger.info(f"[MCPToolRegistry] Tool '{tool_call.name}' executed successfully (from internal server '{server_name}')")
                else:
                    error_msg = f"Tool '{tool_call.name}' does not have execute method"
                    logger.error(f"[MCPToolRegistry] {error_msg}")
                    return ToolResult(
                        tool_name=tool_call.name,
                        success=False,
                        result=None,
                        error=error_msg
                    )
                
                return ToolResult(
                    tool_name=tool_call.name,
                    success=True,
                    result=result
                )
            except Exception as e:
                logger.error(f"[MCPToolRegistry] Error executing tool {tool_call.name}: {e}", exc_info=True)
                return ToolResult(
                    tool_name=tool_call.name,
                    success=False,
                    result=None,
                    error=str(e)
                )
        
        # External tool - use MCP client
        server_name = self._tool_to_server.get(tool_call.name)
        if not server_name:
            error_msg = f"Tool '{tool_call.name}' not found. Available tools: {list(self.tools.keys())}"
            logger.error(f"[MCPToolRegistry] {error_msg}")
            return ToolResult(
                tool_name=tool_call.name,
                success=False,
                result=None,
                error=error_msg
            )
        
        client = self._mcp_clients.get(server_name)
        if not client:
            error_msg = f"MCP client for server '{server_name}' not found"
            logger.error(f"[MCPToolRegistry] {error_msg}")
            return ToolResult(
                tool_name=tool_call.name,
                success=False,
                result=None,
                error=error_msg
            )
        
        try:
            # Call tool via MCP client
            result = await client.call_tool(tool_call.name, tool_call.arguments)
            logger.info(f"[MCPToolRegistry] Tool '{tool_call.name}' executed successfully via external server '{server_name}'")
            
            return ToolResult(
                tool_name=tool_call.name,
                success=True,
                result=result
            )
        except Exception as e:
            logger.error(f"[MCPToolRegistry] Error executing tool {tool_call.name}: {e}", exc_info=True)
            return ToolResult(
                tool_name=tool_call.name,
                success=False,
                result=None,
                error=str(e)
            )
    
    async def get_tool_function_definitions(self) -> list[Dict[str, Any]]:
        """
        Get function definitions for LLM function calling from MCP servers.
        Tool definitions are loaded dynamically from MCP server's list_tools().
        
        Returns:
            List of function definitions in OpenAI format
        """
        # Ensure external tools are loaded
        await self._ensure_external_tools_loaded()
        
        functions = []
        for tool in self.tools.values():
            # Convert MCP Tool format to OpenAI function format
            function_def = {
                "name": tool.get("name", ""),
                "description": tool.get("description", ""),
                "parameters": tool.get("inputSchema", {})
            }
            functions.append(function_def)
        
        logger.info(f"[MCPToolRegistry] Generated {len(functions)} function definitions from MCP servers")
        return functions
    
    def get_tool_function_definitions_sync(self) -> list[Dict[str, Any]]:
        """Synchronous wrapper for get_tool_function_definitions."""
        import asyncio
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        return loop.run_until_complete(self.get_tool_function_definitions())

