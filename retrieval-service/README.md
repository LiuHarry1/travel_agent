# Retrieval Service

RAG retrieval service with multi-embedding models, re-ranking, and LLM-based filtering.

## Features

- **Multi-embedding models**: Query using multiple embedding models simultaneously
- **Deduplication**: Remove duplicate chunks by chunk_id
- **Re-ranking**: Re-rank results based on relevance (mock implementation)
- **LLM filtering**: Use Qwen LLM to filter irrelevant chunks
- **Debug API**: Get intermediate results for each step

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Configure environment variables (create `.env` file):
```env
# Milvus
MILVUS_HOST=localhost
MILVUS_PORT=19530
MILVUS_COLLECTION_NAME=knowledge_base

# Embedding models (comma-separated, format: provider:model)
EMBEDDING_MODELS=qwen:text-embedding-v2,bge:BAAI/bge-large-en-v1.5,openai:text-embedding-3-small

# BGE API (if using BGE via API)
BGE_API_URL=http://localhost:8001

# Qwen LLM
QWEN_API_KEY=your_api_key_here
QWEN_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
QWEN_MODEL=qwen-plus

# Retrieval settings
TOP_K_PER_MODEL=10
RERANK_TOP_K=20
FINAL_TOP_K=10
```

3. Run the service:
```bash
python -m app.main
```

Or using uvicorn:
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8003
```

## API Endpoints

### POST `/api/v1/retrieval/search`

Search for relevant chunks (returns final results only).

**Request:**
```json
{
  "query": "What is the weather like?"
}
```

**Response:**
```json
{
  "query": "What is the weather like?",
  "results": [
    {
      "chunk_id": 123,
      "text": "The weather is sunny today..."
    }
  ]
}
```

### POST `/api/v1/retrieval/search/debug`

Search with debug information (returns all intermediate results).

**Request:**
```json
{
  "query": "What is the weather like?"
}
```

**Response:**
```json
{
  "query": "What is the weather like?",
  "results": [...],
  "debug": {
    "model_results": {
      "qwen:text-embedding-v2": [...],
      "bge:BAAI/bge-large-en-v1.5": [...]
    },
    "deduplicated": [...],
    "reranked": [...],
    "final": [...]
  }
}
```

## Architecture

1. **Multi-embedding search**: Query Milvus with multiple embedding models
2. **Deduplication**: Remove duplicates by chunk_id, keep best score
3. **Re-ranking**: Re-rank results (mock implementation)
4. **LLM filtering**: Use Qwen to filter irrelevant chunks
5. **Return results**: Final chunks with chunk_id and text

