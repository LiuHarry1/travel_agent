export enum ProcessingStage {
  UPLOADING = 'uploading',
  PARSING = 'parsing',
  CHUNKING = 'chunking',
  EMBEDDING = 'embedding',
  INDEXING = 'indexing',
  COMPLETED = 'completed',
  ERROR = 'error',
}

export interface ProcessingProgress {
  stage: ProcessingStage;
  progress: number; // 0-100
  message: string;
  char_count?: number;
  chunks_count?: number;
  embeddings_generated?: number;
  embeddings_total?: number;
  chunks_indexed?: number;
  collection_name?: string;
  filename?: string;
  error_type?: string;
  retryable?: boolean;
}

export interface FileProcessingStatus {
  id: string;
  file: File;
  stage: ProcessingStage;
  progress: number;
  message: string;
  charCount?: number;
  chunksCreated?: number;
  chunksIndexed?: number;
  error?: string;
  errorType?: string;
  retryable?: boolean;
  retryCount: number;
  startTime: number;
  endTime?: number;
}

export interface ProcessingError {
  stage: ProcessingStage;
  error: string;
  errorType?: string;
  retryable: boolean;
  retryCount: number;
}

