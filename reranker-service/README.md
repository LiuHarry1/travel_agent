# Reranker Service

A FastAPI service for document reranking using BGE reranker models.

## Features

- FastAPI-based REST API
- BGE reranker model support (default: `BAAI/bge-reranker-base`)
- Configurable model selection
- Health check endpoint

## Installation

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Set environment variables (optional):
```bash
export RERANKER_MODEL=BAAI/bge-reranker-base  # Default model
export PORT=8009  # Default port
```

## Usage

### Start the service:

```bash
python -m app.main
```

Or using uvicorn directly:
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8009
```

### API Endpoints

#### POST `/api/v1/rerank`

Rerank documents based on query relevance.

**Request:**
```json
{
  "query": "your search query",
  "documents": [
    "document text 1",
    "document text 2",
    ...
  ],
  "top_k": 10,  // Optional: number of top results to return
  "model": "BAAI/bge-reranker-base"  // Optional: model override
}
```

**Response:**
```json
{
  "results": [
    {
      "index": 0,
      "relevance_score": 0.95
    },
    {
      "index": 2,
      "relevance_score": 0.87
    },
    ...
  ]
}
```

#### GET `/health`

Health check endpoint.

**Response:**
```json
{
  "status": "healthy",
  "service": "reranker"
}
```

## Configuration

The service can be configured via environment variables:

- `RERANKER_MODEL`: Model name (default: `BAAI/bge-reranker-base`)
- `PORT`: Server port (default: `8009`)

## Integration with Retrieval Service

To use this service with the retrieval-service, update the pipeline configuration:

```yaml
rerank:
  api_url: http://localhost:8009/api/v1/rerank
  model: BAAI/bge-reranker-base  # Optional
  timeout: 30
```

## Model Options

Supported BGE reranker models:
- `BAAI/bge-reranker-v2-m3` (default, recommended)
- `BAAI/bge-reranker-base` (may require different loading)
- `BAAI/bge-reranker-large` (larger model, slower but more accurate)

Note: If the default model fails to load, the service will automatically try the fallback model.

## Notes

- The model will be downloaded automatically on first use
- Model loading happens at service startup
- The service uses CrossEncoder from sentence-transformers

