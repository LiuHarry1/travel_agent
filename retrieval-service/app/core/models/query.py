"""Query domain model."""
from dataclasses import dataclass
from typing import Optional


@dataclass
class Query:
    """Query value object."""
    
    text: str
    pipeline_name: Optional[str] = None
    
    def __post_init__(self):
        """Validate query."""
        if not self.text or not self.text.strip():
            raise ValueError("Query text cannot be empty")
    
    def __str__(self) -> str:
        return self.text

