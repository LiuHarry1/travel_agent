export interface Collection {
  name: string;
  document_count: number;
  chunk_count: number;
  embedding_dim?: number;
  created_at: string;
  last_updated: string;
}

