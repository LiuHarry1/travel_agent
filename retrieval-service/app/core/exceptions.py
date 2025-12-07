"""Domain exceptions."""


class RetrievalError(Exception):
    """Base exception for retrieval operations."""
    pass


class EmbeddingError(RetrievalError):
    """Exception raised when embedding generation fails."""
    pass


class VectorStoreError(RetrievalError):
    """Exception raised when vector store operations fail."""
    pass


class RerankError(RetrievalError):
    """Exception raised when reranking fails."""
    pass


class LLMFilterError(RetrievalError):
    """Exception raised when LLM filtering fails."""
    pass


class PipelineNotFoundError(RetrievalError):
    """Exception raised when pipeline is not found."""
    pass


class ConfigurationError(RetrievalError):
    """Exception raised when configuration is invalid."""
    pass

