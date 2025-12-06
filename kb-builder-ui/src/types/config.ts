export interface EmbeddingConfig {
  provider: 'qwen' | 'openai' | 'bge';
  model?: string;
  apiKey?: string;
  bgeApiUrl?: string;  // BGE API service URL (e.g., http://10.150.115.110:6000)
}

export interface ChunkingConfig {
  chunkSize: number;
  chunkOverlap: number;
  strategy: 'recursive' | 'semantic' | 'fixed';
}

export interface AppConfig {
  apiUrl: string;
  embedding: EmbeddingConfig;
  chunking: ChunkingConfig;
  defaultCollection: string;
  autoCreateCollection: boolean;
}

export function getDefaultConfig(): AppConfig {
  // Get API URL from environment variable or use default
  const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8001';
  
  return {
    apiUrl,
    embedding: {
      provider: 'openai',  // 改为 openai 或 bge
      model: 'text-embedding-3-small',  // 改为你想要的模型
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

