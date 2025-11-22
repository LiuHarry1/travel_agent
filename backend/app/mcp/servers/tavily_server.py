"""Tavily MCP server."""
from __future__ import annotations

import os

from ..core.base_server import BaseMCPServer
from ..tools.tavily_tool import TavilyTool


def create_tavily_server() -> BaseMCPServer:
    """Create and configure Tavily MCP server."""
    api_key = os.getenv("TAVILY_API_KEY", "")
    tools = [TavilyTool(api_key)] if api_key else []
    return BaseMCPServer("tavily-server", tools)


# For backward compatibility and direct execution
if __name__ == "__main__":
    server = create_tavily_server()
    server.run()

