"""Custom exceptions."""


class KBBuilderError(Exception):
    """Base exception for knowledge base builder."""
    pass


class IndexingError(KBBuilderError):
    """Exception raised during indexing operations."""
    pass


class LoaderError(KBBuilderError):
    """Exception raised during document loading."""
    pass


class EmbeddingError(KBBuilderError):
    """Exception raised during embedding generation."""
    pass


class ChunkerError(KBBuilderError):
    """Exception raised during chunking operations."""
    pass

