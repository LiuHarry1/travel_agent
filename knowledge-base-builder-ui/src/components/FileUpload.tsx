import React, { useState, useCallback } from 'react';
import { FileWithPreview, FileType } from '../types/file';
import type { AppConfig } from '../types/config';
import { apiClient, UploadResponse, BatchUploadResponse } from '../api/client';
import { ProcessingTimeline } from './ProcessingTimeline';
import { ErrorDisplay } from './ErrorDisplay';
import { ProcessingStage, FileProcessingStatus, ProcessingError } from '../types/processing';
import './FileUpload.css';

interface FileUploadProps {
  config: AppConfig;
  collection: string;
  onUploadSuccess?: (result: UploadResponse | BatchUploadResponse) => void;
  onUploadError?: (error: string) => void;
}

const detectFileType = (filename: string | undefined | null): FileType => {
  if (!filename || typeof filename !== 'string') {
    return 'text';
  }
  const ext = filename.split('.').pop()?.toLowerCase();
  const typeMap: Record<string, FileType> = {
    'md': 'markdown',
    'markdown': 'markdown',
    'pdf': 'pdf',
    'docx': 'word',
    'doc': 'word',
    'html': 'html',
    'htm': 'html',
    'txt': 'text',
  };
  return typeMap[ext || ''] || 'text';
};

const formatFileSize = (bytes: number | undefined | null): string => {
  if (!bytes || bytes === 0 || isNaN(bytes)) return '0 Bytes';
  const k = 1024;
  const sizes = ['Bytes', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
};

export const FileUpload: React.FC<FileUploadProps> = ({
  config,
  collection,
  onUploadSuccess,
  onUploadError,
}) => {
  const [files, setFiles] = useState<FileWithPreview[]>([]);
  const [processingFiles, setProcessingFiles] = useState<Map<string, FileProcessingStatus>>(new Map());
  const [uploading, setUploading] = useState(false);

  const handleFileSelect = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      const newFiles: FileWithPreview[] = Array.from(e.target.files)
        .filter((file) => file && file.name) // Filter out invalid files
        .map((file) => {
          // Create a FileWithPreview by creating a new object that extends File
          // We can't modify File properties directly, so we create a wrapper
          const fileWithPreview = Object.create(file) as FileWithPreview;
          // Add our custom properties
          Object.defineProperty(fileWithPreview, 'fileType', {
            value: detectFileType(file.name),
            writable: true,
            enumerable: true,
            configurable: true,
          });
          Object.defineProperty(fileWithPreview, 'status', {
            value: 'pending' as const,
            writable: true,
            enumerable: true,
            configurable: true,
          });
          Object.defineProperty(fileWithPreview, 'progress', {
            value: 0,
            writable: true,
            enumerable: true,
            configurable: true,
          });
          return fileWithPreview;
        });
      setFiles((prev) => [...prev, ...newFiles]);
    }
  }, []);

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
  }, []);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    
    if (e.dataTransfer.files) {
      const newFiles: FileWithPreview[] = Array.from(e.dataTransfer.files)
        .filter((file) => file && file.name) // Filter out invalid files
        .map((file) => {
          // Create a FileWithPreview by creating a new object that extends File
          // We can't modify File properties directly, so we create a wrapper
          const fileWithPreview = Object.create(file) as FileWithPreview;
          // Add our custom properties
          Object.defineProperty(fileWithPreview, 'fileType', {
            value: detectFileType(file.name),
            writable: true,
            enumerable: true,
            configurable: true,
          });
          Object.defineProperty(fileWithPreview, 'status', {
            value: 'pending' as const,
            writable: true,
            enumerable: true,
            configurable: true,
          });
          Object.defineProperty(fileWithPreview, 'progress', {
            value: 0,
            writable: true,
            enumerable: true,
            configurable: true,
          });
          return fileWithPreview;
        });
      setFiles((prev) => [...prev, ...newFiles]);
    }
  }, []);

  const updateFileStatus = useCallback((fileId: string, updates: Partial<FileProcessingStatus>) => {
    setProcessingFiles(prev => {
      const newMap = new Map(prev);
      const existing = newMap.get(fileId);
      if (existing) {
        newMap.set(fileId, { ...existing, ...updates });
      } else {
        const file = files.find(f => f.name === fileId);
        if (file) {
          newMap.set(fileId, {
            id: fileId,
            file,
            stage: ProcessingStage.UPLOADING,
            progress: 0,
            message: '准备上传...',
            retryCount: 0,
            startTime: Date.now(),
            ...updates
          });
        }
      }
      return newMap;
    });
  }, [files]);

  const handleUpload = useCallback(async () => {
    if (files.length === 0) return;

    setUploading(true);

    for (const file of files) {
      const fileId = file.name;
      
      try {
        updateFileStatus(fileId, {
          stage: ProcessingStage.UPLOADING,
          progress: 0,
          message: '开始上传...'
        });

        await apiClient.uploadFileWithProgress(
          file,
          {
            collectionName: collection,
            embeddingProvider: config.embedding.provider,
            embeddingModel: config.embedding.model,
            chunkSize: config.chunking.chunkSize,
            chunkOverlap: config.chunking.chunkOverlap,
          },
          (progress) => {
            const stageMap: Record<string, ProcessingStage> = {
              'uploading': ProcessingStage.UPLOADING,
              'parsing': ProcessingStage.PARSING,
              'chunking': ProcessingStage.CHUNKING,
              'embedding': ProcessingStage.EMBEDDING,
              'indexing': ProcessingStage.INDEXING,
              'completed': ProcessingStage.COMPLETED,
              'error': ProcessingStage.ERROR,
            };

            updateFileStatus(fileId, {
              stage: stageMap[progress.stage] || ProcessingStage.UPLOADING,
              progress: progress.progress,
              message: progress.message,
              charCount: progress.char_count,
              chunksCreated: progress.chunks_count,
              chunksIndexed: progress.chunks_indexed,
              error: progress.stage === 'error' ? progress.message : undefined,
              errorType: progress.error_type,
              retryable: progress.retryable,
              endTime: progress.stage === 'completed' ? Date.now() : undefined,
            });
          }
        );

        // Check completion status after processing
        setTimeout(() => {
          setProcessingFiles(prev => {
            const finalStatus = prev.get(fileId);
            if (finalStatus && finalStatus.stage === ProcessingStage.COMPLETED) {
              // Remove from files list on success
              setFiles(files => files.filter(f => f.name !== fileId));
              
              onUploadSuccess?.({
                success: true,
                filename: file.name,
                document_id: '',
                chunks_indexed: finalStatus.chunksIndexed || 0,
                collection_name: collection,
                message: finalStatus.message,
              });
            }
            return prev;
          });
        }, 100);

      } catch (error) {
        const errorMessage = error instanceof Error ? error.message : 'Upload failed';
        updateFileStatus(fileId, {
          stage: ProcessingStage.ERROR,
          progress: 0,
          message: errorMessage,
          error: errorMessage,
          retryable: true,
        });
        onUploadError?.(errorMessage);
      }
    }

    setUploading(false);
  }, [files, collection, config, onUploadSuccess, onUploadError, processingFiles]);

  const handleRetry = useCallback(async (fileId: string) => {
    let fileStatusToRetry: FileProcessingStatus | undefined;
    
    setProcessingFiles(prev => {
      const fileStatus = prev.get(fileId);
      if (!fileStatus || fileStatus.retryCount >= 3) {
        fileStatusToRetry = fileStatus;
        return prev;
      }
      
      fileStatusToRetry = {
        ...fileStatus,
        retryCount: fileStatus.retryCount + 1,
        stage: ProcessingStage.UPLOADING,
        progress: 0,
        message: `重试中 (${fileStatus.retryCount + 1}/3)...`,
        error: undefined,
      };
      
      const newMap = new Map(prev);
      newMap.set(fileId, fileStatusToRetry);
      return newMap;
    });
    
    if (!fileStatusToRetry || fileStatusToRetry.retryCount > 3) return;

    try {
      await apiClient.uploadFileWithProgress(
        fileStatusToRetry.file,
        {
          collectionName: collection,
          embeddingProvider: config.embedding.provider,
          embeddingModel: config.embedding.model,
          chunkSize: config.chunking.chunkSize,
          chunkOverlap: config.chunking.chunkOverlap,
        },
        (progress) => {
          const stageMap: Record<string, ProcessingStage> = {
            'uploading': ProcessingStage.UPLOADING,
            'parsing': ProcessingStage.PARSING,
            'chunking': ProcessingStage.CHUNKING,
            'embedding': ProcessingStage.EMBEDDING,
            'indexing': ProcessingStage.INDEXING,
            'completed': ProcessingStage.COMPLETED,
            'error': ProcessingStage.ERROR,
          };

          updateFileStatus(fileId, {
            stage: stageMap[progress.stage] || ProcessingStage.UPLOADING,
            progress: progress.progress,
            message: progress.message,
            charCount: progress.char_count,
            chunksCreated: progress.chunks_count,
            chunksIndexed: progress.chunks_indexed,
            error: progress.stage === 'error' ? progress.message : undefined,
            errorType: progress.error_type,
            retryable: progress.retryable,
            endTime: progress.stage === 'completed' ? Date.now() : undefined,
          });
        }
      );
      
      // Check completion after retry
      setTimeout(() => {
        setProcessingFiles(prev => {
          const finalStatus = prev.get(fileId);
          if (finalStatus && finalStatus.stage === ProcessingStage.COMPLETED) {
            onUploadSuccess?.({
              success: true,
              filename: fileStatusToRetry!.file.name,
              document_id: '',
              chunks_indexed: finalStatus.chunksIndexed || 0,
              collection_name: collection,
              message: finalStatus.message,
            });
          }
          return prev;
        });
      }, 100);
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Retry failed';
      updateFileStatus(fileId, {
        stage: ProcessingStage.ERROR,
        progress: 0,
        message: errorMessage,
        error: errorMessage,
      });
    }
  }, [collection, config, updateFileStatus, onUploadSuccess]);

  const removeFile = (index: number) => {
    setFiles(files.filter((_, i) => i !== index));
  };

  const removeProcessingFile = (fileId: string) => {
    setProcessingFiles(prev => {
      const newMap = new Map(prev);
      newMap.delete(fileId);
      return newMap;
    });
  };

  const FileTypeIcon: React.FC<{ type: FileType }> = ({ type }) => {
    const icons: Record<FileType, string> = {
      markdown: '📝',
      pdf: '📄',
      word: '📘',
      html: '🌐',
      text: '📃',
    };
    return <span className="file-icon">{icons[type] || '📄'}</span>;
  };

  return (
    <div className="file-upload-container">
      <h2>Upload Documents to Knowledge Base</h2>
      
      {/* File Drop Zone */}
      <div
        className={`drop-zone ${files.length > 0 ? 'has-files' : ''}`}
        onDragOver={handleDragOver}
        onDrop={handleDrop}
      >
        <input
          type="file"
          id="file-input"
          multiple
          accept=".md,.pdf,.docx,.html,.txt"
          onChange={handleFileSelect}
          style={{ display: 'none' }}
        />
        <label htmlFor="file-input" className="drop-zone-label">
          <div className="drop-zone-icon">📄</div>
          <p>Click to select files or drag and drop</p>
          <p className="drop-zone-hint">
            Supports: .md, .pdf, .docx, .html, .txt
          </p>
        </label>
      </div>

      {/* Selected Files */}
      {files.length > 0 && (
        <div className="files-list">
          <h3>Selected Files ({files.length})</h3>
          {files.map((file, index) => (
            <div key={index} className="file-item">
              <FileTypeIcon type={file.fileType} />
              <span className="file-name">{file.name || 'Unknown file'}</span>
              <span className="file-size">{formatFileSize(file.size)}</span>
              <button
                className="remove-btn"
                onClick={() => removeFile(index)}
                disabled={uploading}
              >
                ×
              </button>
            </div>
          ))}
        </div>
      )}

      {/* Processing Files with Timeline */}
      {processingFiles.size > 0 && (
        <div className="processing-queue-section">
          <h3>处理中的文件 ({processingFiles.size})</h3>
          {Array.from(processingFiles.values()).map((fileStatus, index) => (
            <div key={fileStatus.id || `file-${index}-${fileStatus.startTime || Date.now()}`} className="processing-file-item">
              <div className="file-header">
                <FileTypeIcon type={detectFileType(fileStatus.file?.name)} />
                <span className="file-name">{fileStatus.file?.name || 'Unknown file'}</span>
                <span className={`status-badge ${fileStatus.stage}`}>
                  {fileStatus.stage === ProcessingStage.ERROR ? '失败' : fileStatus.message}
                </span>
                {fileStatus.stage === ProcessingStage.ERROR && fileStatus.retryable && fileStatus.retryCount < 3 && (
                  <button className="retry-small-btn" onClick={() => handleRetry(fileStatus.id)}>
                    重试
                  </button>
                )}
                <button className="remove-btn" onClick={() => removeProcessingFile(fileStatus.id)}>
                  ×
                </button>
              </div>
              <ProcessingTimeline fileStatus={fileStatus} />
              
              {fileStatus.stage === ProcessingStage.ERROR && fileStatus.error && (
                <ErrorDisplay
                  error={{
                    stage: fileStatus.stage,
                    error: fileStatus.error,
                    errorType: fileStatus.errorType,
                    retryable: fileStatus.retryable || false,
                    retryCount: fileStatus.retryCount,
                  }}
                  onRetry={() => handleRetry(fileStatus.id)}
                  onDismiss={() => removeProcessingFile(fileStatus.id)}
                />
              )}
            </div>
          ))}
        </div>
      )}

      {/* Upload Button */}
      <button
        className="upload-btn"
        onClick={handleUpload}
        disabled={files.length === 0 || uploading}
      >
        {uploading ? 'Processing...' : `Upload ${files.length} File(s)`}
      </button>
    </div>
  );
};
