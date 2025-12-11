"""File management utilities for loaders."""
from pathlib import Path
from typing import Optional
import shutil
import uuid
from utils.logger import get_logger

logger = get_logger(__name__)


class FileManager:
    """Manages file operations for document loaders."""
    
    def __init__(self, static_dir: Path):
        """
        Args:
            static_dir: Static files root directory
        """
        self.static_dir = Path(static_dir)
        self.sources_dir = self.static_dir / "sources"
        
        # Ensure directories exist
        self.sources_dir.mkdir(parents=True, exist_ok=True)
    
    def generate_file_id(self, filename: str) -> str:
        """Generate unique file ID."""
        return f"{uuid.uuid4().hex[:8]}_{Path(filename).stem}"
    
    def save_source_file(
        self, 
        source_path: Path, 
        file_id: Optional[str] = None,
        original_filename: Optional[str] = None
    ) -> Path:
        """
        Save source file to sources directory.
        
        Args:
            source_path: Path to source file
            file_id: Optional file ID (will be generated if not provided)
            original_filename: Optional original filename (uses source_path.name if not provided)
        
        Returns:
            Path to saved file
        """
        if file_id is None:
            original_filename = original_filename or source_path.name
            file_id = self.generate_file_id(original_filename)
        
        # Keep original extension
        ext = source_path.suffix
        saved_path = self.sources_dir / f"{file_id}{ext}"
        
        shutil.copy2(source_path, saved_path)
        logger.debug(f"Saved source file to: {saved_path}")
        
        return saved_path
