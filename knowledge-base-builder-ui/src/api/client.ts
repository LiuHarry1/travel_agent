const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8001';

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

  async listCollections(): Promise<Collection[]> {
    const response = await fetch(`${this.baseUrl}/api/v1/collections`);
    if (!response.ok) {
      throw new Error('Failed to fetch collections');
    }
    const data = await response.json();
    return data.collections || [];
  }

  async createCollection(name: string, embeddingDim: number = 1536): Promise<void> {
    const formData = new FormData();
    formData.append('name', name);
    formData.append('embedding_dim', embeddingDim.toString());
    
    const response = await fetch(`${this.baseUrl}/api/v1/collections`, {
      method: 'POST',
      body: formData,
    });
    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to create collection');
    }
  }

  async deleteCollection(name: string): Promise<void> {
    const response = await fetch(`${this.baseUrl}/api/v1/collections/${encodeURIComponent(name)}`, {
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

  uploadFileWithProgress(
    file: File,
    options: {
      collectionName?: string;
      embeddingProvider?: string;
      embeddingModel?: string;
      chunkSize?: number;
      chunkOverlap?: number;
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
      if (options.chunkSize !== undefined && options.chunkSize !== null) {
        formData.append('chunk_size', options.chunkSize.toString());
      }
      if (options.chunkOverlap !== undefined && options.chunkOverlap !== null) {
        formData.append('chunk_overlap', options.chunkOverlap.toString());
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

          const readStream = (): void => {
            reader.read().then(({ done, value }) => {
              if (done) {
                // Process any remaining buffer
                if (buffer.trim()) {
                  processBuffer(buffer);
                }
                resolve();
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

              readStream();
            }).catch(reject);
          };

          const processBuffer = (line: string) => {
            if (line.startsWith('data: ')) {
              try {
                const data = JSON.parse(line.substring(6));
                onProgress(data);
                
                if (data.stage === 'completed') {
                  resolve();
                  return;
                }
                if (data.stage === 'error') {
                  reject(new Error(data.message));
                  return;
                }
              } catch (e) {
                // Ignore parse errors for malformed JSON
                console.warn('Failed to parse progress data:', line);
              }
            }
          };

          readStream();
        })
        .catch(reject);
    });
  }
}

export const apiClient = new ApiClient();

