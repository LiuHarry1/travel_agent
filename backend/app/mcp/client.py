"""MCP client for connecting to MCP servers."""
from __future__ import annotations

import asyncio
import json
import logging
import subprocess
from typing import Any, Dict, List, Optional

try:
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client
    MCP_AVAILABLE = True
except ImportError:
    MCP_AVAILABLE = False
    logger = logging.getLogger(__name__)
    logger.warning("MCP SDK not available, using fallback implementation")

logger = logging.getLogger(__name__)


class MCPClient:
    """Client for connecting to MCP servers via stdio."""
    
    def __init__(self, command: str, args: List[str], env: Optional[Dict[str, str]] = None):
        """
        Initialize MCP client.
        
        Args:
            command: Command to start the MCP server (e.g., "python", "npx")
            args: Arguments for the command (e.g., ["-m", "app.mcp.faq.server"])
            env: Environment variables to pass to the server process
        """
        self.command = command
        self.args = args
        self.env = env or {}
        self.session: Optional[ClientSession] = None
        self._initialized = False
        self._tools: List[Dict[str, Any]] = []
        
        # Create server parameters with environment variables
        if MCP_AVAILABLE:
            # StdioServerParameters may or may not support env parameter
            # Try with env first, fallback without if it fails
            try:
                self._server_params = StdioServerParameters(
                    command=command,
                    args=args,
                    env=env if env else None
                )
            except TypeError:
                # If env parameter is not supported, create without it
                # We'll handle env in subprocess manually if needed
                self._server_params = StdioServerParameters(
                    command=command,
                    args=args
                )
        else:
            self._server_params = None
    
    async def initialize(self) -> None:
        """Initialize connection to MCP server and get tools list."""
        if self._initialized:
            return
        
        if not MCP_AVAILABLE:
            logger.error("[MCPClient] MCP SDK not available. Please install mcp package.")
            raise RuntimeError("MCP SDK not available")
        
        try:
            # Create stdio client connection
            async with stdio_client(self._server_params) as (read, write):
                async with ClientSession(read, write) as session:
                    # Initialize the session
                    await session.initialize()
                    
                    # Get tools list
                    tools_result = await session.list_tools()
                    self._tools = [
                        {
                            "name": tool.name,
                            "description": tool.description,
                            "inputSchema": tool.inputSchema
                        }
                        for tool in tools_result.tools
                    ]
                    
                    logger.info(f"[MCPClient] Connected to server and loaded {len(self._tools)} tools")
                    
                    # Store session for later use (note: this won't work with context manager)
                    # We need to keep the connection alive
                    self.session = session
                    self._initialized = True
                    
        except Exception as e:
            logger.error(f"[MCPClient] Failed to initialize connection: {e}", exc_info=True)
            raise
    
    async def list_tools(self) -> List[Dict[str, Any]]:
        """Get list of tools from MCP server."""
        if not self._initialized:
            await self.initialize()
        
        return self._tools
    
    async def call_tool(self, name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Call a tool on the MCP server.
        
        Args:
            name: Tool name
            arguments: Tool arguments
            
        Returns:
            Tool result
        """
        if not MCP_AVAILABLE:
            raise RuntimeError("MCP SDK not available")
        
        if not self._initialized:
            await self.initialize()
        
        # Recreate connection for each call (since we can't keep it alive easily)
        async with stdio_client(self._server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                
                # Call the tool
                result = await session.call_tool(name, arguments)
                
                # Extract text content from result
                if result.content and len(result.content) > 0:
                    # Get text from first content item
                    text = result.content[0].text if hasattr(result.content[0], 'text') else str(result.content[0])
                    # Try to parse as JSON, otherwise return as text
                    try:
                        return json.loads(text)
                    except json.JSONDecodeError:
                        return {"text": text}
        
        return {}
    
    def close(self) -> None:
        """Close the connection to MCP server."""
        # Session is managed by context manager, so we just mark as uninitialized
        self._initialized = False
        self.session = None

