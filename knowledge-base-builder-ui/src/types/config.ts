export interface MilvusConfig {
  host: string;
  port: number;
  user?: string;
  password?: string;
  alias?: string;
}

export interface EmbeddingConfig {
  provider: 'qwen' | 'openai' | 'bge';
  model?: string;
  apiKey?: string;
}

export interface ChunkingConfig {
  chunkSize: number;
  chunkOverlap: number;
  strategy: 'recursive' | 'semantic' | 'fixed';
}

export interface AppConfig {
  milvus: MilvusConfig;
  embedding: EmbeddingConfig;
  chunking: ChunkingConfig;
  defaultCollection: string;
  autoCreateCollection: boolean;
}

export function getDefaultConfig(): AppConfig {
  return {
    milvus: {
      host: 'localhost',
      port: 19530,
      user: '',
      password: '',
    },
    embedding: {
      provider: 'qwen',
      model: 'text-embedding-v2',
    },
    chunking: {
      chunkSize: 1000,
      chunkOverlap: 200,
      strategy: 'recursive',
    },
    defaultCollection: 'knowledge_base',
    autoCreateCollection: true,
  };
}

