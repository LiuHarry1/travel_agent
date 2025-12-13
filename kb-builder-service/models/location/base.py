"""Base location model."""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, Any, Optional


@dataclass
class BaseLocation(ABC):
    """Base class for chunk location information."""
    
    # Common fields - only character position
    start_char: int = 0
    end_char: int = 0
    
    # Flexible metadata for type-specific fields
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @abstractmethod
    def to_dict(self) -> Dict[str, Any]:
        """
        Serialize to dictionary for storage.
        
        Returns:
            Dictionary representation
        """
        pass
    
    @classmethod
    @abstractmethod
    def from_dict(cls, data: Dict[str, Any]) -> "BaseLocation":
        """
        Deserialize from dictionary.
        
        Args:
            data: Dictionary representation
        
        Returns:
            Location instance
        """
        pass
    
    @abstractmethod
    def get_citation(self) -> str:
        """
        Generate citation text for RAG.
        
        Returns:
            Citation string
        """
        pass
    
    @abstractmethod
    def get_navigation_url(self, base_url: str, document_id: str) -> str:
        """
        Generate navigation URL for frontend.
        
        Args:
            base_url: Base URL for API
            document_id: Document identifier
        
        Returns:
            Navigation URL
        """
        pass
    
    def get_common_fields(self) -> Dict[str, Any]:
        """Get common fields for serialization."""
        return {
            "start_char": self.start_char,
            "end_char": self.end_char,
        }

