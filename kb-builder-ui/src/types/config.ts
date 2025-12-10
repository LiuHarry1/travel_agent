export interface EmbeddingConfig {
  provider: 'qwen' | 'openai' | 'bge' | 'bge-en' | 'bge-zh' | 'nemotron' | 'nvidia' | 'snowflake';
  model?: string;
  apiKey?: string;  // For qwen and openai
  bgeApiUrl?: string;  // For bge provider (general BGE API URL)
  bgeEnApiUrl?: string;  // For bge-en provider (English BGE API URL)
  bgeZhApiUrl?: string;  // For bge-zh provider (Chinese BGE API URL)
  nemotronApiUrl?: string;  // For nemotron/nvidia provider
  snowflakeApiUrl?: string;  // For snowflake provider
  openaiBaseUrl?: string;  // Optional base URL for OpenAI (for custom endpoints)
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
  const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8005';
  
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

