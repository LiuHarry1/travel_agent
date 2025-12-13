"""PDF location tracker."""
from typing import List
from models.document import Document
from models.chunk import Chunk
from models.location.markdown_location import MarkdownLocation
from .base import LocationTracker
from utils.logger import get_logger

logger = get_logger(__name__)


class PDFLocationTracker(LocationTracker):
    """PDF-specific location tracker (uses MarkdownLocation)."""
    
    def track_during_loading(self, document: Document) -> Document:
        """
        Track location information during document loading.
        
        For PDF, we can preprocess the document structure here if needed.
        Currently, location information is extracted during chunking.
        
        Args:
            document: Document object
        
        Returns:
            Document with location information tracked
        """
        # PDF location tracking is primarily done during chunking
        # This method can be used to build location indices if needed
        return document
    
    def track_during_chunking(
        self,
        chunks: List[Chunk],
        document: Document
    ) -> List[Chunk]:
        """
        Track and enrich location information during chunking.
        
        In unified Markdown architecture, location is already created by chunker.
        This method only ensures source is set in metadata.
        
        Args:
            chunks: List of Chunk objects
            document: Document object
        
        Returns:
            List of Chunks with enriched location information
        """
        for chunk in chunks:
            if not chunk.location:
                # Create location from chunk metadata if missing
                chunk.location = self._create_location_from_chunk(chunk, document)
            else:
                # Ensure source is set in location metadata
                if "source" not in chunk.location.metadata:
                    chunk.location.metadata["source"] = document.metadata.get("file_name", document.source)
        
        return chunks
    
    def _create_location_from_chunk(
        self,
        chunk: Chunk,
        document: Document
    ) -> MarkdownLocation:
        """Create MarkdownLocation from chunk metadata."""
        metadata = chunk.metadata
        
        location = MarkdownLocation(
            start_char=metadata.get("start_pos", 0),
            end_char=metadata.get("end_pos", len(chunk.text)),
            metadata={
                "source": document.metadata.get("file_name", document.source),
            }
        )
        
        return location

