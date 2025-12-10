"""Chatbot API routes."""
from __future__ import annotations

import base64
import json
from typing import Dict, Any

from fastapi import APIRouter, Depends, File, UploadFile, HTTPException
from fastapi.responses import StreamingResponse

from ..llm import LLMError
from ..models import ChatRequest, GenerateTitleRequest, GenerateTitleResponse
from ..utils.constants import MAX_FILE_SIZE_BYTES, BINARY_FILE_PREFIX, BINARY_FILE_SUFFIX, SUPPORTED_EXTENSIONS
from ..utils.exceptions import format_error_message
from ..utils.file_utils import is_text_file
from .dependencies import get_chat_service

router = APIRouter()


@router.post("/agent/message/stream")
async def agent_message_stream(
    request: ChatRequest,
    chat_service = Depends(get_chat_service),
) -> StreamingResponse:
    """Handle chat request with streaming response and tool calling events (async implementation)."""
    
    async def generate():
        """Async generator for streaming SSE events with full async implementation."""
        try:
            # Use async generator directly - no threads needed!
            # This provides true async concurrency with minimal overhead
            async for event in chat_service.chat_stream(request):
                # Format as SSE
                data = json.dumps(event, ensure_ascii=False)
                yield f"data: {data}\n\n"
            
            # Send done signal
            yield "data: " + json.dumps({"type": "done"}, ensure_ascii=False) + "\n\n"
            
        except LLMError as exc:
            error_msg = format_error_message(exc, "Error processing request")
            error_data = json.dumps({"type": "error", "content": error_msg}, ensure_ascii=False)
            yield f"data: {error_data}\n\n"
        except Exception as exc:
            error_msg = format_error_message(exc, "An error occurred while processing your request")
            error_data = json.dumps({"type": "error", "content": error_msg}, ensure_ascii=False)
            yield f"data: {error_data}\n\n"
    
    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/agent/generate-title")
async def generate_title(
    request: GenerateTitleRequest,
    chat_service = Depends(get_chat_service),
) -> GenerateTitleResponse:
    """Generate a concise title for a conversation based on its content."""
    try:
        title = await chat_service.generate_conversation_title(request.messages)
        return GenerateTitleResponse(title=title)
    except Exception as exc:
        # If title generation fails, return a fallback
        error_msg = format_error_message(exc, "Failed to generate title")
        # Use first user message as fallback
        fallback_title = "New chat"
        for msg in request.messages:
            if msg.get("role") == "user" and msg.get("content"):
                fallback_title = msg["content"][:30].strip() or "New chat"
                break
        return GenerateTitleResponse(title=fallback_title)


@router.post("/upload/file")
async def upload_file(file: UploadFile = File(...)) -> Dict[str, Any]:
    """
    Upload a file and return its content.
    
    Supports text files (returned as plain text) and binary files 
    (PDF, Word - returned as base64 encoded with marker).
    """
    try:
        # Validate file size
        file_content = await file.read()
        file_size = len(file_content)
        
        if file_size > MAX_FILE_SIZE_BYTES:
            raise HTTPException(
                status_code=413,
                detail=f"File too large. Maximum size is {MAX_FILE_SIZE_BYTES / (1024 * 1024):.1f}MB"
            )
        
        # Check file extension
        file_name = file.filename or "unknown"
        file_ext = None
        for ext in SUPPORTED_EXTENSIONS:
            if file_name.lower().endswith(ext):
                file_ext = ext
                break
        
        if file_ext is None:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported file type. Supported types: {', '.join(SUPPORTED_EXTENSIONS)}"
            )
        
        # Process file content based on type
        if is_text_file(file_name):
            # Text file - return as plain text
            try:
                content = file_content.decode('utf-8')
            except UnicodeDecodeError:
                raise HTTPException(
                    status_code=400,
                    detail="File is not valid UTF-8 text. Please use a text file or convert to PDF/Word."
                )
        else:
            # Binary file - encode as base64 with marker
            base64_content = base64.b64encode(file_content).decode('utf-8')
            content = f"{BINARY_FILE_PREFIX}{file_ext}:{base64_content}{BINARY_FILE_SUFFIX}"
        
        return {
            "filename": file_name,
            "content": content,
            "size": file_size
        }
        
    except HTTPException:
        raise
    except Exception as exc:
        error_msg = format_error_message(exc, "Failed to upload file")
        raise HTTPException(status_code=500, detail=error_msg) from exc

