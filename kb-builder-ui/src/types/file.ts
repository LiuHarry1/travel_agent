export type FileType = 'markdown' | 'pdf' | 'word' | 'html' | 'text';

export interface FileWithPreview extends File {
  preview?: string;
  fileType: FileType; // Renamed from 'type' to avoid conflict with File.type (MIME type)
  status: 'pending' | 'processing' | 'success' | 'error';
  progress: number;
  result?: any;
  error?: string;
}

export interface ProcessingItem {
  id: string;
  filename: string;
  type: FileType;
  status: 'pending' | 'processing' | 'success' | 'error';
  progress: number;
  result?: any;
  error?: string;
}

