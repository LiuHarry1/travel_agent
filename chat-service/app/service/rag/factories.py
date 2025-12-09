"""Factory classes for RAG sources and strategies."""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Type

from .sources.base import BaseRetrievalSource
from .sources.retrieval_service import RetrievalServiceSource
from .strategies.base import BaseRetrievalStrategy
from .strategies.single_round import SingleRoundStrategy
from .strategies.multi_round import MultiRoundStrategy
from .strategies.parallel import ParallelStrategy

logger = logging.getLogger(__name__)


class SourceFactory:
    """Factory for creating retrieval sources."""
    
    _source_classes: Dict[str, Type[BaseRetrievalSource]] = {}
    
    @classmethod
    def register(cls, source_type: str, source_class: Type[BaseRetrievalSource]) -> None:
        """
        Register a source type.
        
        Args:
            source_type: Type identifier (e.g., "retrieval_service")
            source_class: Source class that implements BaseRetrievalSource
        """
        cls._source_classes[source_type] = source_class
        logger.debug(f"Registered retrieval source type: {source_type}")
    
    @classmethod
    def create(cls, source_type: str, config: Dict[str, Any]) -> BaseRetrievalSource:
        """
        Create a source instance.
        
        Args:
            source_type: Type identifier
            config: Source configuration
            
        Returns:
            BaseRetrievalSource instance
            
        Raises:
            ValueError: If source type is not registered
        """
        if source_type not in cls._source_classes:
            raise ValueError(
                f"Unknown source type: {source_type}. "
                f"Registered types: {list(cls._source_classes.keys())}"
            )
        
        source_class = cls._source_classes[source_type]
        try:
            return source_class(config)
        except Exception as e:
            logger.error(f"Failed to create source {source_type}: {e}", exc_info=True)
            raise ValueError(f"Failed to create source {source_type}: {str(e)}") from e
    
    @classmethod
    def get_registered_types(cls) -> List[str]:
        """Get list of registered source types."""
        return list(cls._source_classes.keys())


class StrategyFactory:
    """Factory for creating retrieval strategies."""
    
    _strategy_classes: Dict[str, Type[BaseRetrievalStrategy]] = {}
    
    @classmethod
    def register(cls, strategy_type: str, strategy_class: Type[BaseRetrievalStrategy]) -> None:
        """
        Register a strategy type.
        
        Args:
            strategy_type: Type identifier (e.g., "multi_round")
            strategy_class: Strategy class that implements BaseRetrievalStrategy
        """
        cls._strategy_classes[strategy_type] = strategy_class
        logger.debug(f"Registered retrieval strategy type: {strategy_type}")
    
    @classmethod
    def create(
        cls,
        strategy_type: str,
        sources: List[BaseRetrievalSource],
        config: Dict[str, Any]
    ) -> BaseRetrievalStrategy:
        """
        Create a strategy instance.
        
        Args:
            strategy_type: Type identifier
            sources: List of retrieval sources
            config: Strategy configuration
            
        Returns:
            BaseRetrievalStrategy instance
            
        Raises:
            ValueError: If strategy type is not registered
        """
        if strategy_type not in cls._strategy_classes:
            raise ValueError(
                f"Unknown strategy type: {strategy_type}. "
                f"Registered types: {list(cls._strategy_classes.keys())}"
            )
        
        strategy_class = cls._strategy_classes[strategy_type]
        try:
            return strategy_class(sources, config)
        except Exception as e:
            logger.error(f"Failed to create strategy {strategy_type}: {e}", exc_info=True)
            raise ValueError(f"Failed to create strategy {strategy_type}: {str(e)}") from e
    
    @classmethod
    def get_registered_types(cls) -> List[str]:
        """Get list of registered strategy types."""
        return list(cls._strategy_classes.keys())


# Register default sources and strategies
def _register_defaults():
    """Register default source and strategy types."""
    # Register default sources
    SourceFactory.register("retrieval_service", RetrievalServiceSource)
    
    # Register default strategies
    StrategyFactory.register("single_round", SingleRoundStrategy)
    StrategyFactory.register("multi_round", MultiRoundStrategy)
    StrategyFactory.register("parallel", ParallelStrategy)


# Auto-register on import
_register_defaults()

