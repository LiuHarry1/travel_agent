"""FAQ search function"""
from __future__ import annotations

from typing import Any, Dict

# 复用现有的 FAQTool 逻辑
from app.tools.implementations.faq_tool import FAQTool

_faq_tool_instance = None


def _get_faq_tool():
    """获取 FAQ tool 实例（单例）"""
    global _faq_tool_instance
    if _faq_tool_instance is None:
        _faq_tool_instance = FAQTool()
    return _faq_tool_instance


async def faq_search(query: str) -> Dict[str, Any]:
    """
    Search FAQ knowledge base.
    
    Args:
        query: Search query in Chinese
    
    Returns:
        Dict with answer, matched_question, score, etc.
    """
    tool = _get_faq_tool()
    result = await tool.execute({"query": query})
    
    if result.success:
        return result.data
    else:
        return {
            "answer": None,
            "found": False,
            "message": result.error or "FAQ search failed",
            "source": "travel_faq_database"
        }


# Function schema for LLM
FAQ_SCHEMA = {
    "type": "object",
    "properties": {
        "query": {
            "type": "string",
            "description": "The travel-related question to search in FAQ knowledge base. Must be in Chinese (中文) and travel-related."
        }
    },
    "required": ["query"]
}

