# Knowledge Base Builder

A simple, extensible tool for indexing documents into vector databases for RAG (Retrieval-Augmented Generation) applications.

## Features

- 📄 **Multiple Document Types**: Support for Markdown, PDF, DOCX, HTML, and TXT files
- 🔪 **Flexible Chunking**: Configurable text chunking with overlap
- 🧠 **Multiple Embedding Providers**: Qwen, OpenAI, and BGE (BAAI General Embedding)
- 💾 **Vector Storage**: Milvus integration for vector storage
- 🚀 **Easy to Use**: Simple CLI tool for quick testing
- 🔧 **Extensible**: Plugin-based architecture for easy extension

## Installation

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Set up environment variables (create `.env` file):
```bash
# For Qwen embeddings
DASHSCOPE_API_KEY=your_dashscope_api_key

# For OpenAI embeddings (optional)
OPENAI_API_KEY=your_openai_api_key

# Milvus configuration (optional, defaults shown)
MILVUS_HOST=localhost
MILVUS_PORT=19530
MILVUS_USER=
MILVUS_PASSWORD=
```

## Quick Start

### Using the CLI Script

The easiest way to test indexing is using the provided CLI script:

```bash
# Index a markdown file with default settings
python index_document.py document.md

# Index with custom collection and embedding provider
python index_document.py document.md --collection my_kb --embedding-provider qwen

# Index with custom chunk size
python index_document.py document.md --chunk-size 2000 --chunk-overlap 400

# Index with BGE embeddings
python index_document.py document.md --embedding-provider bge --embedding-model BAAI/bge-large-en-v1.5
```

### CLI Options

```
positional arguments:
  file_path             Path to the document file

optional arguments:
  --doc-type {markdown,pdf,docx,html,txt}
                        Document type (default: markdown)
  --collection COLLECTION
                        Collection name (default: from config)
  --embedding-provider {qwen,openai,bge}
                        Embedding provider (default: from config)
  --embedding-model EMBEDDING_MODEL
                        Embedding model name (default: from config)
  --chunk-size CHUNK_SIZE
                        Chunk size in characters (default: from config)
  --chunk-overlap CHUNK_OVERLAP
                        Chunk overlap in characters (default: from config)
  --milvus-host MILVUS_HOST
                        Milvus host (default: from config)
  --milvus-port MILVUS_PORT
                        Milvus port (default: from config)
  --milvus-user MILVUS_USER
                        Milvus user (default: from config)
  --milvus-password MILVUS_PASSWORD
                        Milvus password (default: from config)
  --verbose, -v         Enable verbose logging
```

### Using as Python Library

```python
from models.document import DocumentType
from services.indexing_service import IndexingService
from processors.stores import MilvusVectorStore

# Create vector store
vector_store = MilvusVectorStore(
    host="localhost",
    port=19530
)

# Create service
service = IndexingService(
    vector_store=vector_store,
    chunk_size=1000,
    chunk_overlap=200
)

# Index document
result = service.index_document(
    source="document.md",
    doc_type=DocumentType.MARKDOWN,
    collection_name="knowledge_base",
    embedding_provider="qwen",
    embedding_model="text-embedding-v2"
)

print(f"Indexed {result['chunks_indexed']} chunks")
```

## Architecture

The project follows a simple, extensible architecture:

```
kb_builder/
├── models/          # Data models (Document, Chunk)
├── processors/       # Processors (loaders, chunkers, embedders, stores)
├── services/         # Business logic (IndexingService)
├── config/          # Configuration management
└── utils/           # Utilities and exceptions
```

### Adding New Components

#### Add a New Document Loader

```python
from processors.loaders.base import BaseLoader
from models.document import Document, DocumentType

class MyLoader(BaseLoader):
    def load(self, source: str, **kwargs) -> Document:
        # Your loading logic
        pass
    
    def supports(self, doc_type: DocumentType) -> bool:
        return doc_type == DocumentType.MY_TYPE

# Register it
from processors.loaders.factory import LoaderFactory
LoaderFactory.register(DocumentType.MY_TYPE, MyLoader)
```

#### Add a New Embedding Provider

```python
from processors.embedders.base import BaseEmbedder

class MyEmbedder(BaseEmbedder):
    def embed(self, texts: List[str]) -> List[List[float]]:
        # Your embedding logic
        pass
    
    @property
    def dimension(self) -> int:
        return 768

# Register it in EmbedderFactory
```

## Configuration

Configuration can be set via:
1. Environment variables (see `.env.example`)
2. Pydantic settings (defaults in `config/settings.py`)
3. CLI arguments (overrides all)

## Requirements

- Python 3.10+
- Milvus server (for vector storage)
- API keys for embedding providers (Qwen/OpenAI)

## License

MIT

