"""Function Registry - 统一管理所有函数"""
from __future__ import annotations

import inspect
import json
import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from app.utils.constants import BACKEND_ROOT
from app.tools.implementations.config_manager import ConfigManager

logger = logging.getLogger(__name__)


@dataclass
class FunctionDefinition:
    """函数定义"""
    name: str
    description: str
    schema: Dict[str, Any]  # JSON Schema
    func: Callable
    type: str = "local"  # "local" or "external_api"
    enabled: bool = True
    config: Optional[Dict[str, Any]] = None


class FunctionRegistry:
    """统一的函数注册表"""
    
    def __init__(self, config_path: Optional[str] = None):
        """
        初始化函数注册表
        
        Args:
            config_path: 配置文件路径，默认为 None（使用统一的 app.yaml）
        """
        if config_path is None:
            # Use unified app.yaml instead of separate functions.yaml
            config_path = str(BACKEND_ROOT / "config" / "app.yaml")
        self.config_path = Path(config_path)
        self._config_manager = ConfigManager(self.config_path)
        self._functions: Dict[str, FunctionDefinition] = {}
        self._enabled_functions: set[str] = set()
    
    def register_function(
        self,
        name: str,
        func: Callable,
        schema: Dict[str, Any],
        description: str,
        type: str = "local",
        enabled: bool = True,
        config: Optional[Dict[str, Any]] = None
    ):
        """
        注册函数
        
        Args:
            name: 函数名
            func: 函数实现
            schema: JSON Schema
            description: 函数描述
            type: 函数类型 ("local" or "external_api")
            enabled: 是否默认启用
            config: 函数配置
        """
        # Validate function signature matches schema
        self._validate_function_signature(func, schema)
        
        self._functions[name] = FunctionDefinition(
            name=name,
            description=description,
            schema=schema,
            func=func,
            type=type,
            enabled=enabled,
            config=config
        )
        if enabled:
            self._enabled_functions.add(name)
        logger.info(f"Registered function: {name} (type: {type}, enabled: {enabled})")
    
    def _validate_function_signature(self, func: Callable, schema: Dict[str, Any]) -> None:
        """
        验证函数签名与 schema 是否匹配
        
        Args:
            func: 函数实现
            schema: JSON Schema
            
        Raises:
            ValueError: 如果签名不匹配
        """
        try:
            sig = inspect.signature(func)
            schema_properties = schema.get("properties", {})
            schema_required = schema.get("required", [])
            
            # Check required parameters
            param_names = set(sig.parameters.keys())
            # Remove 'self' or 'cls' for methods
            param_names.discard("self")
            param_names.discard("cls")
            
            # Check if all required schema params exist in function signature
            missing_params = set(schema_required) - param_names
            if missing_params:
                logger.warning(
                    f"Function {func.__name__} missing required parameters from schema: {missing_params}"
                )
                # Don't raise error, just warn - some functions might have optional params
        except Exception as e:
            logger.warning(f"Failed to validate function signature for {func.__name__}: {e}")
            # Don't raise - validation is best effort
    
    def enable_function(self, name: str):
        """启用函数"""
        if name in self._functions:
            self._functions[name].enabled = True
            self._enabled_functions.add(name)
            logger.info(f"Enabled function: {name}")
        else:
            raise ValueError(f"Function not found: {name}")
    
    def disable_function(self, name: str):
        """禁用函数"""
        if name in self._functions:
            self._functions[name].enabled = False
            self._enabled_functions.discard(name)
            logger.info(f"Disabled function: {name}")
        else:
            raise ValueError(f"Function not found: {name}")
    
    def get_enabled_functions(self) -> List[str]:
        """获取启用的函数列表"""
        return list(self._enabled_functions)
    
    def get_all_functions(self) -> List[FunctionDefinition]:
        """获取所有函数"""
        return list(self._functions.values())
    
    def get_function(self, name: str) -> Optional[FunctionDefinition]:
        """获取函数定义"""
        return self._functions.get(name)
    
    async def call_function(
        self, 
        name: str, 
        arguments: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> Any:
        """
        调用函数
        
        Args:
            name: 函数名
            arguments: 函数参数
            context: 额外上下文（如 conversation_history）
        """
        if name not in self._functions:
            raise ValueError(f"Function not found: {name}")
        
        func_def = self._functions[name]
        if not func_def.enabled:
            raise ValueError(f"Function is disabled: {name}")
        
        # 对于 RAG 函数，如果支持 conversation_history，则传递
        if name == "retrieval_service_search" and context:
            conversation_history = context.get("conversation_history")
            if conversation_history is not None:
                # Check if function accepts conversation_history parameter
                import inspect
                sig = inspect.signature(func_def.func)
                if "conversation_history" in sig.parameters:
                    arguments["conversation_history"] = conversation_history
        
        # 如果是异步函数，使用 await
        import inspect
        if inspect.iscoroutinefunction(func_def.func):
            return await func_def.func(**arguments)
        else:
            return func_def.func(**arguments)
    
    def get_function_definitions_for_llm(self) -> List[Dict[str, Any]]:
        """获取启用的函数定义（OpenAI 格式）"""
        functions = []
        for name in self._enabled_functions:
            func_def = self._functions[name]
            functions.append({
                "name": func_def.name,
                "description": func_def.description,
                "parameters": func_def.schema
            })
        return functions
    
    @property
    def functions(self) -> Dict[str, FunctionDefinition]:
        """获取所有函数（只读）"""
        return self._functions.copy()
    
    def save_config(self) -> None:
        """保存配置到文件"""
        function_configs = {
            name: func_def.config
            for name, func_def in self._functions.items()
            if func_def.config
        }
        self._config_manager.save(
            enabled_functions=list(self._enabled_functions),
            function_configs=function_configs
        )
    
    def load_config(self) -> None:
        """从文件加载配置"""
        enabled, configs = self._config_manager.load()
        
        # Load enabled functions
        for name in enabled:
            if name in self._functions:
                self.enable_function(name)
            else:
                logger.warning(f"Function {name} not found in registry, skipping")
        
        # Load function configs
        for name, func_config in configs.items():
            if name in self._functions:
                if self._functions[name].config is None:
                    self._functions[name].config = {}
                self._functions[name].config.update(func_config)


# 全局函数注册表实例
_function_registry: Optional[FunctionRegistry] = None


def get_function_registry() -> FunctionRegistry:
    """获取全局函数注册表实例"""
    global _function_registry
    if _function_registry is None:
        _function_registry = FunctionRegistry()
        _initialize_functions(_function_registry)
    return _function_registry


def reset_function_registry():
    """重置函数注册表（用于测试）"""
    global _function_registry
    _function_registry = None


def _initialize_functions(registry: FunctionRegistry):
    """初始化所有函数"""
    from .functions import faq, rag_search
    
    # 注册 FAQ 函数
    registry.register_function(
        name="faq_search",
        func=faq.faq_search,
        schema=faq.FAQ_SCHEMA,
        description="Travel FAQ Tool: Search travel-related FAQ database for pre-approved answers. Must be in Chinese (中文) and travel-related.",
        type="local",
        enabled=True
    )
    
    # 注册 Retrieval Service 函数（RAG）
    retrieval_service_url = os.getenv(
        "RETRIEVAL_SERVICE_URL",
        "http://localhost:8003"
    )
    
    registry.register_function(
        name="retrieval_service_search",
        func=rag_search.retrieval_service_search,
        schema=rag_search.RETRIEVAL_SERVICE_SCHEMA,
        description="RAG Search Tool: Search knowledge base using retrieval service. Use this for comprehensive document retrieval. Supports context-aware query generation and multi-turn retrieval.",
        type="external_api",
        enabled=False,  # 默认禁用，用户可以在 UI 中启用
        config={
            "api_url": retrieval_service_url,
            "pipeline_name": "default",
            "timeout": 30,
            "max_search_iterations": 3
        }
    )
    
    # 加载配置（覆盖默认设置）
    registry.load_config()
    
    logger.info(
        f"Initialized function registry: {len(registry._functions)} functions, "
        f"{len(registry._enabled_functions)} enabled"
    )

