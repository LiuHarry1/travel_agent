"""FastAPI dependencies for dependency injection."""
from __future__ import annotations

from fastapi import Depends

from ..core.container import Container, get_container
from ..core.config_service import ConfigurationService, get_config_service
from ..service.chat import ChatService
from ..service.message_processing import MessageProcessingService
from ..service.tool_execution import ToolExecutionService
from ..service.rag import RAGOrchestrator


def get_container_dep() -> Container:
    """Dependency to get container instance."""
    return get_container()


def get_config_service_dep() -> ConfigurationService:
    """Dependency to get configuration service instance."""
    return get_config_service()


def get_chat_service(container: Container = Depends(get_container_dep)) -> ChatService:
    """Dependency to get chat service instance."""
    return container.chat_service


def get_message_processor(container: Container = Depends(get_container_dep)) -> MessageProcessingService:
    """Dependency to get message processing service instance."""
    return container.message_processor


def get_tool_executor(container: Container = Depends(get_container_dep)) -> ToolExecutionService:
    """Dependency to get tool execution service instance."""
    return container.tool_executor


def get_rag_orchestrator(container: Container = Depends(get_container_dep)) -> RAGOrchestrator:
    """Dependency to get RAG orchestrator instance."""
    return container.rag_orchestrator

