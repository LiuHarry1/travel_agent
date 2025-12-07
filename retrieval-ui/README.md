# Retrieval UI

React frontend for the retrieval system debug interface.

## Features

- **Query Input**: Enter questions to search
- **Multi-step Results Display**: View results from each step:
  - Results from each embedding model
  - After deduplication
  - After re-ranking
  - Final LLM-filtered results
- **Expandable Sections**: Collapse/expand each step for better organization
- **Chunk Details**: View chunk ID, text, scores, and embedder information

## Setup

1. Install dependencies:
```bash
npm install
```

2. Configure API URL (optional, defaults to http://localhost:8003):
Create `.env` file:
```env
VITE_API_BASE_URL=http://localhost:8003
```

3. Run development server:
```bash
npm run dev
```

4. Build for production:
```bash
npm run build
```

## Usage

1. Enter a query in the search box
2. Click "Search" to retrieve results
3. Expand each section to view intermediate results:
   - **Model Results**: Results from each embedding model
   - **After Deduplication**: Results after removing duplicates by chunk_id
   - **After Re-ranking**: Results after re-ranking
   - **Final Results**: Results after LLM filtering

Each chunk card shows:
- Chunk ID
- Embedder name (for model results)
- Score (distance from query)
- Rerank score (if available)
- Chunk text content

