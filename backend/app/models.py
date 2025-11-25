from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ChecklistItem(BaseModel):
    id: str = Field(..., description="Checklist identifier")
    description: str = Field(..., description="Description of the checklist item")


class ChatRequest(BaseModel):
    session_id: Optional[str] = Field(
        default=None,
        description="Existing session identifier. Leave empty to start a new session.",
    )
    message: Optional[str] = Field(
        default=None,
        description="Free form user message to the agent.",
    )
    messages: Optional[List[Dict[str, str]]] = Field(
        default=None,
        description="Full conversation history from frontend. Format: [{'role': 'user/assistant', 'content': '...'}, ...]",
    )

    files: Optional[List[Dict[str, str]]] = Field(
        default=None,
        description="List of uploaded files with name and content. Format: [{'name': '...', 'content': '...'}, ...]",
    )


class ConfigUpdateRequest(BaseModel):
    system_prompt_template: str = Field(..., description="System prompt template. Use {tools} placeholder for available tools list.")
    checklist: Optional[List[ChecklistItem]] = Field(default=None, description="Checklist items to save (optional, for backward compatibility)")


class ToolCall(BaseModel):
    """Represents a tool call in the conversation."""
    id: Optional[str] = Field(default=None, description="Tool call ID")
    name: str = Field(..., description="Tool name")
    arguments: Dict[str, Any] = Field(..., description="Tool call arguments")
