import type { EmbeddingConfig } from '../types/config';

/**
 * Get embedding dimension based on provider and model.
 */
export function getEmbeddingDimension(config: EmbeddingConfig): number {
  const { provider, model } = config;
  
  switch (provider) {
    case 'qwen':
      // Qwen embeddings are typically 1536 dimensions
      return 1536;
    
    case 'openai':
      // OpenAI embeddings vary by model
      if (model?.includes('3-large')) {
        return 3072;
      }
      // text-embedding-3-small, text-embedding-ada-002, etc. are 1536
      return 1536;
    
    case 'bge':
      // BGE embeddings vary by model
      if (!model) {
        return 1024; // Default to large
      }
      
      if (model.includes('large')) {
        return 1024;
      } else if (model.includes('base')) {
        return 768;
      } else if (model.includes('small')) {
        return 384;
      } else if (model.includes('nemotron')) {
        return 1024;
      }
      
      // Default to large if unknown
      return 1024;
    
    default:
      // Default to 1536 (Qwen/OpenAI standard)
      return 1536;
  }
}

