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
  // Multi-granularity chunking
  useMultiGranularity: boolean;
  multiGranularitySizes: number[];
  multiGranularityOverlap: number;
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
  const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8006';
  
  return {
    apiUrl,
    embedding: {
      provider: 'openai',  // Change to openai or bge
      model: 'text-embedding-3-small',  // Change to your desired model
    },
    chunking: {
      chunkSize: 1000,
      chunkOverlap: 200,
      strategy: 'recursive',
      useMultiGranularity: false,
      multiGranularitySizes: [200, 400, 800],
      multiGranularityOverlap: 60,
    },
    defaultCollection: 'knowledge_base',
    autoCreateCollection: true,
  };
}

