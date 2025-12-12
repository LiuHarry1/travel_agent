const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8006';

export interface UploadResponse {
  success: boolean;
  filename: string;
  document_id: string;
  chunks_indexed: number;
  collection_name: string;
  message: string;
}

export interface BatchUploadResponse {
  success: boolean;
  total_files: number;
  results: Array<{
    filename: string;
    success: boolean;
    chunks_indexed?: number;
    message: string;
  }>;
}

export interface Collection {
  name: string;
  document_count: number;
  chunk_count: number;
  created_at: string;
  last_updated: string;
}

export interface SourceFile {
  document_id: string;
  filename: string;
  chunk_count: number;
  file_path?: string;  // Actual file path for accessing the file
}

export interface ChunkLocation {
  start_char?: number;
  end_char?: number;
  page_number?: number;
  page_bbox?: { x0: number; y0: number; x1: number; y1: number };
  paragraph_index?: number;
  section_index?: number;
  heading_path?: string[];
  code_block_index?: number;
  image_index?: number;
  image_url?: string;
  table_index?: number;
  table_cell?: string;
}

export interface Chunk {
  id: number;
  text: string;
  document_id: string;
  index: number;
  metadata?: Record<string, any>;
  location?: ChunkLocation;
  file_path?: string;
  chunk_id?: string;
}

export interface ChunksResponse {
  success: boolean;
  collection_name: string;
  document_id: string;
  chunks: Chunk[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface MilvusConfigRequest {
  host: string;
  port: number;
  user?: string;
  password?: string;
}

export class ApiClient {
  private baseUrl: string;

  constructor(baseUrl: string = API_BASE_URL) {
    this.baseUrl = baseUrl;
  }

  async uploadFile(
    file: File,
    options: {
      collectionName?: string;
      embeddingProvider?: string;
      embeddingModel?: string;
      bgeApiUrl?: string;
      chunkSize?: number;
      chunkOverlap?: number;
    } = {}
  ): Promise<UploadResponse> {
    const formData = new FormData();
    formData.append('file', file);
    
    if (options.collectionName) {
      formData.append('collection_name', options.collectionName);
    }
    if (options.embeddingProvider) {
      formData.append('embedding_provider', options.embeddingProvider);
    }
    if (options.embeddingModel) {
      formData.append('embedding_model', options.embeddingModel);
    }
    if (options.bgeApiUrl) {
      formData.append('bge_api_url', options.bgeApiUrl);
    }
    if (options.chunkSize) {
      formData.append('chunk_size', options.chunkSize.toString());
    }
    if (options.chunkOverlap) {
      formData.append('chunk_overlap', options.chunkOverlap.toString());
    }

    const response = await fetch(`${this.baseUrl}/api/v1/upload`, {
      method: 'POST',
      body: formData,
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Upload failed');
    }

    return response.json();
  }

  async uploadBatch(
    files: File[],
    options: {
      collectionName?: string;
      embeddingProvider?: string;
      embeddingModel?: string;
      bgeApiUrl?: string;
    } = {}
  ): Promise<BatchUploadResponse> {
    const formData = new FormData();
    
    files.forEach(file => {
      formData.append('files', file);
    });
    
    if (options.collectionName) {
      formData.append('collection_name', options.collectionName);
    }
    if (options.embeddingProvider) {
      formData.append('embedding_provider', options.embeddingProvider);
    }
    if (options.embeddingModel) {
      formData.append('embedding_model', options.embeddingModel);
    }
    if (options.bgeApiUrl) {
      formData.append('bge_api_url', options.bgeApiUrl);
    }

    const response = await fetch(`${this.baseUrl}/api/v1/upload/batch`, {
      method: 'POST',
      body: formData,
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Batch upload failed');
    }

    return response.json();
  }

  async listCollections(database?: string): Promise<Collection[]> {
    const url = new URL(`${this.baseUrl}/api/v1/collections`);
    if (database) {
      url.searchParams.append('database', database);
    }
    const response = await fetch(url.toString());
    if (!response.ok) {
      throw new Error('Failed to fetch collections');
    }
    const data = await response.json();
    return data.collections || [];
  }

  async createCollection(name: string, embeddingDim: number = 1536, database?: string): Promise<void> {
    const formData = new FormData();
    formData.append('name', name);
    formData.append('embedding_dim', embeddingDim.toString());
    if (database) {
      formData.append('database', database);
    }
    
    const response = await fetch(`${this.baseUrl}/api/v1/collections`, {
      method: 'POST',
      body: formData,
    });
    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to create collection');
    }
  }

  async deleteCollection(name: string, database?: string): Promise<void> {
    const url = new URL(`${this.baseUrl}/api/v1/collections/${encodeURIComponent(name)}`);
    if (database) {
      url.searchParams.append('database', database);
    }
    const response = await fetch(url.toString(), {
      method: 'DELETE',
    });
    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to delete collection');
    }
  }

  async testMilvusConnection(config: MilvusConfigRequest): Promise<{ success: boolean; message: string }> {
    const response = await fetch(`${this.baseUrl}/api/v1/config/test-milvus`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(config),
    });
    return response.json();
  }

  async getDefaultConfig(): Promise<any> {
    const response = await fetch(`${this.baseUrl}/api/v1/config/defaults`);
    if (!response.ok) {
      throw new Error('Failed to fetch default config');
    }
    return response.json();
  }

  async healthCheck(): Promise<{ status: string; service: string }> {
    const response = await fetch(`${this.baseUrl}/api/v1/health`);
    return response.json();
  }

  async listSources(collectionName: string, database?: string): Promise<SourceFile[]> {
    const url = new URL(`${this.baseUrl}/api/v1/collections/${encodeURIComponent(collectionName)}/sources`);
    if (database) {
      url.searchParams.append('database', database);
    }
    const response = await fetch(url.toString());
    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to fetch sources');
    }
    const data = await response.json();
    return data.sources || [];
  }

  async getSourceChunks(
    collectionName: string,
    documentId: string,
    page: number = 1,
    pageSize: number = 10,
    database?: string
  ): Promise<ChunksResponse> {
    const params = new URLSearchParams({
      page: page.toString(),
      page_size: pageSize.toString(),
    });
    if (database) {
      params.append('database', database);
    }
    const response = await fetch(
      `${this.baseUrl}/api/v1/collections/${encodeURIComponent(collectionName)}/sources/${encodeURIComponent(documentId)}/chunks?${params}`
    );
    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to fetch chunks');
    }
    const data = await response.json();
    console.log('=== Raw Backend Response ===');
    console.log('Response data:', data);
    if (data && data.chunks && data.chunks.length > 0) {
      console.log('Raw first chunk:', JSON.stringify(data.chunks[0], null, 2));
    }
    return data;
  }

  async getSourceFileUrl(collectionName: string, documentId: string, database?: string): Promise<string> {
    const url = new URL(
      `${this.baseUrl}/api/v1/collections/${encodeURIComponent(collectionName)}/sources/${encodeURIComponent(documentId)}/file`
    );
    if (database) {
      url.searchParams.append('database', database);
    }
    const response = await fetch(url.toString());
    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to get source file URL');
    }
    const data = await response.json();
    // Return full URL if it starts with http, otherwise construct it
    if (data.file_url.startsWith('http')) {
      return data.file_url;
    }
    // If relative URL, prepend baseUrl
    return `${this.baseUrl}${data.file_url}`;
  }

  async deleteSource(collectionName: string, documentId: string, database?: string): Promise<void> {
    const url = new URL(
      `${this.baseUrl}/api/v1/collections/${encodeURIComponent(collectionName)}/sources/${encodeURIComponent(documentId)}`
    );
    if (database) {
      url.searchParams.append('database', database);
    }
    const response = await fetch(url.toString(), {
      method: 'DELETE',
    });
    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to delete source');
    }
  }

  async listDatabases(): Promise<{ databases: string[]; current: string }> {
    const response = await fetch(`${this.baseUrl}/api/v1/databases`);
    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to fetch databases');
    }
    const data = await response.json();
    return {
      databases: data.databases || [],
      current: data.current || 'default'
    };
  }

  async createDatabase(name: string): Promise<void> {
    const formData = new FormData();
    formData.append('name', name);
    
    const response = await fetch(`${this.baseUrl}/api/v1/databases`, {
      method: 'POST',
      body: formData,
    });
    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to create database');
    }
  }

  async deleteDatabase(name: string): Promise<void> {
    const response = await fetch(`${this.baseUrl}/api/v1/databases/${encodeURIComponent(name)}`, {
      method: 'DELETE',
    });
    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to delete database');
    }
  }

  uploadFileWithProgress(
    file: File,
    options: {
      collectionName?: string;
      embeddingProvider?: string;
      embeddingModel?: string;
      bgeApiUrl?: string;
      chunkSize?: number;
      chunkOverlap?: number;
      multiGranularitySizes?: number[];
      multiGranularityOverlap?: number;
      database?: string;
    },
    onProgress: (progress: any) => void
  ): Promise<void> {
    return new Promise((resolve, reject) => {
      // Validate file object
      if (!(file instanceof File)) {
        reject(new Error('Invalid file object. Expected File instance.'));
        return;
      }

      const formData = new FormData();
      formData.append('file', file, file.name);
      
      // Always append all fields, even if optional, to avoid validation issues
      if (options.collectionName) {
        formData.append('collection_name', options.collectionName);
      }
      if (options.embeddingProvider) {
        formData.append('embedding_provider', options.embeddingProvider);
      }
      if (options.embeddingModel) {
        formData.append('embedding_model', options.embeddingModel);
      }
      if (options.bgeApiUrl) {
        formData.append('bge_api_url', options.bgeApiUrl);
      }
      if (options.chunkSize !== undefined && options.chunkSize !== null) {
        formData.append('chunk_size', options.chunkSize.toString());
      }
      if (options.chunkOverlap !== undefined && options.chunkOverlap !== null) {
        formData.append('chunk_overlap', options.chunkOverlap.toString());
      }
      if (options.multiGranularitySizes && options.multiGranularitySizes.length > 0) {
        formData.append('multi_granularity_chunk_sizes', JSON.stringify(options.multiGranularitySizes));
      }
      if (options.multiGranularityOverlap !== undefined && options.multiGranularityOverlap !== null) {
        formData.append('multi_granularity_chunk_overlap', options.multiGranularityOverlap.toString());
      }
      if (options.database) {
        formData.append('database', options.database);
      }

      // Use fetch with ReadableStream for SSE
      // Note: Don't set Content-Type header - browser will set it automatically with boundary
      fetch(`${this.baseUrl}/api/v1/upload/stream`, {
        method: 'POST',
        body: formData,
        // Don't set headers - let browser set Content-Type with boundary for multipart/form-data
      })
        .then(response => {
          if (!response.ok) {
            // Try to get error details from response
            return response.json().then(errorData => {
              console.error('Upload error:', errorData);
              const errorMsg = errorData.detail?.[0]?.msg || `HTTP error! status: ${response.status}`;
              throw new Error(errorMsg);
            }).catch(() => {
              throw new Error(`HTTP error! status: ${response.status}`);
            });
          }
          
          const reader = response.body?.getReader();
          const decoder = new TextDecoder();
          
          if (!reader) {
            throw new Error('No response body');
          }

          let buffer = '';

          let isCompleted = false;
          let isError = false;
          let completedNotified = false; // Track if completed notification has been sent
          
          const processBuffer = (line: string) => {
            if (line.startsWith('data: ')) {
              try {
                const data = JSON.parse(line.substring(6));
                console.log('Progress update received:', data); // Debug log
                
                // Prevent processing multiple completed messages
                if (data.stage === 'completed') {
                  if (completedNotified) {
                    console.log('Duplicate completed message ignored');
                    return;
                  }
                  completedNotified = true;
                  console.log('Processing completed');
                  isCompleted = true;
                  onProgress(data); // Call onProgress before resolve
                  resolve();
                  return;
                }
                
                // Don't process any more messages after completion
                if (isCompleted || completedNotified) {
                  return;
                }
                
                if (data.stage === 'error') {
                  console.error('Processing error:', data.message);
                  isError = true;
                  onProgress(data); // Call onProgress before reject
                  reject(new Error(data.message));
                  return;
                }
                
                // Process other stages normally
                onProgress(data);
              } catch (e) {
                // Ignore parse errors for malformed JSON
                console.warn('Failed to parse progress data:', line, e);
              }
            } else if (line.trim()) {
              // Log non-data lines for debugging
              console.log('Received non-data line:', line);
            }
          };
          
          const readStream = (): void => {
            reader.read().then(({ done, value }) => {
              if (done) {
                // Process any remaining buffer
                if (buffer.trim()) {
                  processBuffer(buffer);
                }
                // If stream ended without completion or error, something went wrong
                if (!isCompleted && !isError) {
                  console.warn('Stream ended without completion or error message');
                  reject(new Error('Stream ended unexpectedly without completion'));
                }
                return;
              }

              buffer += decoder.decode(value, { stream: true });
              const lines = buffer.split('\n');
              
              // Keep the last incomplete line in buffer
              buffer = lines.pop() || '';

              // Process complete lines
              for (const line of lines) {
                if (line.trim()) {
                  processBuffer(line);
                }
              }

              // Continue reading only if not completed or errored
              if (!isCompleted && !isError) {
                readStream();
              }
            }).catch((error) => {
              console.error('Stream read error:', error);
              reject(error);
            });
          };

          readStream();
        })
        .catch(reject);
    });
  }
}

// Default API client instance (will be updated when config changes)
let defaultApiClient = new ApiClient();

// Function to get API client with custom URL
export function getApiClient(baseUrl?: string): ApiClient {
  if (baseUrl) {
    return new ApiClient(baseUrl);
  }
  return defaultApiClient;
}

// Function to update default API client URL
export function updateApiClientUrl(baseUrl: string) {
  defaultApiClient = new ApiClient(baseUrl);
}

// Export default instance
export const apiClient = defaultApiClient;

