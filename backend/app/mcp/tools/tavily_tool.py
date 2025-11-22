"""Tavily search tool implementation."""
from __future__ import annotations

import logging
import os
from typing import Any, Dict

try:
    import httpx
    HTTPX_AVAILABLE = True
except ImportError:
    HTTPX_AVAILABLE = False

from ..core.base_tool import BaseMCPTool, ToolExecutionResult


class TavilyTool(BaseMCPTool):
    """Tool for searching the web using Tavily API."""
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize Tavily tool.
        
        Args:
            api_key: Tavily API key. If not provided, will try to get from environment.
        """
        super().__init__(
            name="tavily_search",
            description="Search the web using Tavily API for real-time information, news, and data extraction"
        )
        self.api_key = api_key or os.getenv("TAVILY_API_KEY", "")
        self.base_url = "https://api.tavily.com"
        
        if not self.api_key:
            self.logger.warning("TAVILY_API_KEY not set. Tool will not function properly.")
    
    def get_input_schema(self) -> Dict[str, Any]:
        """Get input schema for Tavily tool."""
        return {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The search query to find information on the web"
                },
                "max_results": {
                    "type": "integer",
                    "description": "Maximum number of search results to return",
                    "default": 5,
                    "minimum": 1,
                    "maximum": 10
                },
                "search_depth": {
                    "type": "string",
                    "description": "Search depth: 'basic' for faster results or 'advanced' for more comprehensive results",
                    "enum": ["basic", "advanced"],
                    "default": "basic"
                }
            },
            "required": ["query"]
        }
    
    async def execute(self, arguments: Dict[str, Any]) -> ToolExecutionResult:
        """
        Execute Tavily search.
        
        Args:
            arguments: Tool arguments containing:
                - query (str): Search query
                - max_results (int, optional): Maximum number of results (default: 5)
                - search_depth (str, optional): "basic" or "advanced" (default: "basic")
        
        Returns:
            ToolExecutionResult with search results
        """
        if not HTTPX_AVAILABLE:
            return ToolExecutionResult(
                success=False,
                data=None,
                error="httpx package is required. Please install it: pip install httpx"
            )
        
        if not self.api_key:
            return ToolExecutionResult(
                success=False,
                data=None,
                error="TAVILY_API_KEY not configured. Please set TAVILY_API_KEY environment variable."
            )
        
        query = arguments.get("query", "")
        max_results = arguments.get("max_results", 5)
        search_depth = arguments.get("search_depth", "basic")
        
        if not query:
            return ToolExecutionResult(
                success=False,
                data=None,
                error="Query parameter is required"
            )
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.base_url}/search",
                    json={
                        "api_key": self.api_key,
                        "query": query,
                        "max_results": max_results,
                        "search_depth": search_depth
                    },
                    headers={
                        "Content-Type": "application/json"
                    }
                )
                response.raise_for_status()
                result = response.json()
                
                return ToolExecutionResult(
                    success=True,
                    data={
                        "query": query,
                        "results": result.get("results", []),
                        "answer": result.get("answer", ""),
                        "response_time": result.get("response_time", 0)
                    },
                    metadata={
                        "response_time": result.get("response_time", 0),
                        "result_count": len(result.get("results", []))
                    }
                )
        except httpx.HTTPError as e:
            self.logger.error(f"HTTP error: {e}")
            return ToolExecutionResult(
                success=False,
                data=None,
                error=f"HTTP error: {str(e)}"
            )
        except Exception as e:
            self.logger.error(f"Error executing search: {e}", exc_info=True)
            return ToolExecutionResult(
                success=False,
                data=None,
                error=f"Error executing search: {str(e)}"
            )

