from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


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


class GenerateTitleRequest(BaseModel):
    """Request model for generating conversation title."""
    messages: List[Dict[str, str]] = Field(
        ...,
        description="Conversation history to generate title from. Format: [{'role': 'user/assistant', 'content': '...'}, ...]",
    )


class GenerateTitleResponse(BaseModel):
    """Response model for generated title."""
    title: str = Field(..., description="Generated conversation title")