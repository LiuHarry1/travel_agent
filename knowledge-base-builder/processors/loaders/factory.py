"""Loader factory."""
from typing import Dict, Type, Optional
from .base import BaseLoader
from .markdown import MarkdownLoader
from .unified_loader import UnifiedLoader
from models.document import DocumentType
from config.settings import get_settings


class LoaderFactory:
    """Factory for creating document loaders."""
    
    _loaders: Dict[DocumentType, Type[BaseLoader]] = {
        DocumentType.MARKDOWN: MarkdownLoader,
    }
    
    # 使用统一加载器作为默认加载器
    _use_unified_loader = True
    
    @classmethod
    def create(cls, doc_type: DocumentType, static_dir: Optional[str] = None, base_url: Optional[str] = None) -> BaseLoader:
        """Create loader for document type."""
        # 如果启用统一加载器，使用 UnifiedLoader
        if cls._use_unified_loader:
            if static_dir is None or base_url is None:
                # 从配置获取或使用默认值
                try:
                    settings = get_settings()
                    if static_dir is None:
                        static_dir = getattr(settings, 'static_dir', 'static')
                    if base_url is None:
                        base_url = getattr(settings, 'static_base_url', '')
                except:
                    if static_dir is None:
                        static_dir = 'static'
                    if base_url is None:
                        base_url = ''
            return UnifiedLoader(static_dir=static_dir, base_url=base_url)
        
        # 否则使用注册的加载器
        loader_class = cls._loaders.get(doc_type)
        if not loader_class:
            raise ValueError(f"No loader available for type: {doc_type}")
        return loader_class()
    
    @classmethod
    def register(cls, doc_type: DocumentType, loader_class: Type[BaseLoader]):
        """Register a new loader type."""
        cls._loaders[doc_type] = loader_class
    
    @classmethod
    def set_use_unified_loader(cls, use: bool):
        """设置是否使用统一加载器"""
        cls._use_unified_loader = use

