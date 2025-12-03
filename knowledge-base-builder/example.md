# Knowledge Base Builder Example Document

This is an example markdown document for testing the knowledge base builder.

## Introduction

The Knowledge Base Builder is a tool for indexing documents into vector databases. It supports multiple document types, embedding providers, and vector stores.

## Features

### Document Types

- Markdown files (.md)
- PDF documents (.pdf)
- Word documents (.docx)
- HTML files (.html)
- Plain text files (.txt)

### Embedding Providers

1. **Qwen**: Alibaba DashScope embedding API
2. **OpenAI**: OpenAI embedding API
3. **BGE**: BAAI General Embedding models

### Vector Stores

- Milvus (primary support)
- More stores can be added easily

## Usage

To index a document, use the CLI script:

```bash
python index_document.py document.md --collection my_kb
```

## Architecture

The project follows a simple, extensible architecture with clear separation of concerns:

- **Models**: Data structures (Document, Chunk)
- **Processors**: Pluggable components (loaders, chunkers, embedders, stores)
- **Services**: Business logic (IndexingService)
- **Config**: Configuration management

## Conclusion

This tool makes it easy to build knowledge bases for RAG applications.

