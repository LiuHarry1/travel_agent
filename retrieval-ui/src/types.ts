export interface ChunkResult {
  chunk_id: number
  text: string
}

export interface DebugChunkResult extends ChunkResult {
  score?: number
  rerank_score?: number
  embedder?: string
}

export interface RetrievalResponse {
  query: string
  results: ChunkResult[]
}

export interface DebugRetrievalResponse extends RetrievalResponse {
  debug: {
    model_results: Record<string, DebugChunkResult[]>
    deduplicated: DebugChunkResult[]
    reranked: DebugChunkResult[]
    final: DebugChunkResult[]
    timing?: {
      embedding_total?: number
      [key: string]: number | undefined
      deduplication?: number
      rerank?: number
      llm_filter?: number
      total?: number
    }
  }
}

