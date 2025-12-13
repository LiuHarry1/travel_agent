"""Base structure class for all document types."""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, Any, Optional, List


@dataclass
class BaseStructure(ABC):
    """Base class for all document structure types."""
    
    # Common fields
    tables: Optional[List[Dict]] = None  # Table list (all types may have tables)
    
    @abstractmethod
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        pass
    
    def get_common_fields(self) -> Dict[str, Any]:
        """Get common fields for serialization."""
        result = {}
        if self.tables is not None:
            result["tables"] = self.tables
        return result

