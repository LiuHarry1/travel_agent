# Knowledge Base Builder API

FastAPI backend for document indexing and vector store management.

## Features

- 📤 File upload and indexing
- 📚 Collection management
- ⚙️ Configuration testing
- 🔍 Health checks

## API Endpoints

### File Upload

#### POST `/api/v1/upload`
Upload and index a single file.

**Form Data:**
- `file`: File to upload (required)
- `collection_name`: Collection name (optional)
- `embedding_provider`: qwen, openai, or bge (optional, default: qwen)
- `embedding_model`: Model name (optional)
- `chunk_size`: Chunk size in characters (optional)
- `chunk_overlap`: Chunk overlap in characters (optional)

**Response:**
```json
{
  "success": true,
  "filename": "document.md",
  "document_id": "/tmp/...",
  "chunks_indexed": 10,
  "collection_name": "knowledge_base",
  "message": "Successfully indexed 10 chunks"
}
```

#### POST `/api/v1/upload/batch`
Upload and index multiple files.

**Form Data:**
- `files`: Array of files (required)
- `collection_name`: Collection name (optional)
- `embedding_provider`: Embedding provider (optional)

### Collections

#### GET `/api/v1/collections`
List all collections.

**Response:**
```json
{
  "collections": [
    {
      "name": "knowledge_base",
      "document_count": 0,
      "chunk_count": 100,
      "created_at": "",
      "last_updated": ""
    }
  ]
}
```

#### POST `/api/v1/collections`
Create a new collection.

**Form Data:**
- `name`: Collection name (required)
- `embedding_dim`: Embedding dimension (optional, default: 1536)

#### DELETE `/api/v1/collections/{name}`
Delete a collection.

### Configuration

#### POST `/api/v1/config/test-milvus`
Test Milvus connection.

**Request Body:**
```json
{
  "host": "localhost",
  "port": 19530,
  "user": "",
  "password": ""
}
```

#### GET `/api/v1/config/defaults`
Get default configuration.

### Health

#### GET `/api/v1/health`
Health check endpoint.

## Running the Server

```bash
cd knowledge-base-builder
pip install -r requirements.txt
python main.py
```

Server will run on `http://localhost:8001`

API documentation available at `http://localhost:8001/docs`

