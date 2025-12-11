import React, { useState, useCallback, useRef } from 'react';
import { FileText, File, BookOpen, Globe, FileCode, X, Book, ChevronDown, ChevronUp } from 'lucide-react';
import { FileWithPreview, FileType } from '../types/file';
import type { AppConfig } from '../types/config';
import { apiClient, UploadResponse, BatchUploadResponse } from '../api/client';
import { ProcessingTimeline } from './ProcessingTimeline';
import { ErrorDisplay } from './ErrorDisplay';
import { ProcessingStage, FileProcessingStatus } from '../types/processing';
import './FileUpload.css';

interface FileUploadProps {
  config: AppConfig;
  collection: string;
  database?: string;
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
  database,
  onUploadSuccess,
  onUploadError,
}) => {
  const [files, setFiles] = useState<FileWithPreview[]>([]);
  const [processingFiles, setProcessingFiles] = useState<Map<string, FileProcessingStatus>>(new Map());
  const [uploading, setUploading] = useState(false);
  const [expandedFiles, setExpandedFiles] = useState<Set<string>>(new Set());
  const [filesCollapsed, setFilesCollapsed] = useState(false); // Control whether Selected Files is collapsed
  const successNotifiedRef = useRef<Set<string>>(new Set()); // Use ref to synchronously track successfully notified files

  const handleFileSelect = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      const newFiles: FileWithPreview[] = Array.from(e.target.files)
        .filter((file) => file && file.name) // Filter out invalid files
        .map((file) => {
          // Create a FileWithPreview by directly assigning properties to the File object
          // This preserves all File methods and properties with correct 'this' context
          const fileWithPreview = file as unknown as FileWithPreview;
          // Add our custom properties directly (they will be on the object, not on the prototype)
          (fileWithPreview as any).fileType = detectFileType(file.name);
          (fileWithPreview as any).status = 'pending';
          (fileWithPreview as any).progress = 0;
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
          // Create a FileWithPreview by wrapping the File object
          // We use a Proxy or direct assignment to preserve File methods
          const fileWithPreview = file as unknown as FileWithPreview;
          // Add our custom properties directly (they will be on the object, not on the prototype)
          (fileWithPreview as any).fileType = detectFileType(file.name);
          (fileWithPreview as any).status = 'pending';
          (fileWithPreview as any).progress = 0;
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
            message: 'Preparing to upload...',
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
    setFilesCollapsed(true); // Auto-collapse Selected Files to give Processing Files more space
    successNotifiedRef.current.clear(); // Clear previous notification records, start new upload batch

    for (const file of files) {
      const fileId = file.name;
      
      try {
        updateFileStatus(fileId, {
          stage: ProcessingStage.UPLOADING,
          progress: 0,
          message: 'Starting upload...'
        });

        await apiClient.uploadFileWithProgress(
          file,
          {
            collectionName: collection,
            embeddingProvider: config.embedding.provider,
            embeddingModel: config.embedding.model,
            bgeApiUrl: config.embedding.bgeApiUrl,
            chunkSize: config.chunking.chunkSize,
            chunkOverlap: config.chunking.chunkOverlap,
            database: database,
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

            const isCompleted = progress.stage === 'completed';
            
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
              endTime: isCompleted ? Date.now() : undefined,
            });

            // Handle completion directly in progress callback to avoid duplicate notifications
            if (isCompleted) {
              // Use ref for synchronous check to prevent duplicate notifications
              if (successNotifiedRef.current.has(fileId)) {
                // Already notified, skip
                return;
              }
              
              // Mark as notified immediately (synchronous)
              successNotifiedRef.current.add(fileId);
              
              // Remove from files list on success
              setFiles(files => files.filter(f => f.name !== fileId));
              
              // Call success callback only once
              onUploadSuccess?.({
                success: true,
                filename: file.name,
                document_id: '',
                chunks_indexed: progress.chunks_indexed || 0,
                collection_name: collection,
                message: progress.message || 'File processed successfully',
              });
            }
          }
        );

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
    // Remove from success notified when retrying
    successNotifiedRef.current.delete(fileId);
    
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
        message: `Retrying (${fileStatus.retryCount + 1}/3)...`,
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
          bgeApiUrl: config.embedding.bgeApiUrl,
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

          const isCompleted = progress.stage === 'completed';
          
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
            endTime: isCompleted ? Date.now() : undefined,
          });

          // Handle completion directly in progress callback to avoid duplicate notifications
          if (isCompleted) {
            // Use ref for synchronous check to prevent duplicate notifications
            if (successNotifiedRef.current.has(fileId)) {
              // Already notified, skip
              return;
            }
            
            // Mark as notified immediately (synchronous)
            successNotifiedRef.current.add(fileId);
            
            // Call success callback only once
            onUploadSuccess?.({
              success: true,
              filename: fileStatusToRetry!.file.name,
              document_id: '',
              chunks_indexed: progress.chunks_indexed || 0,
              collection_name: collection,
              message: progress.message || 'File processed successfully',
            });
          }
        }
      );
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

  // Clear all state, return to initial upload state
  const handleClearAll = useCallback(() => {
    setFiles([]);
    setProcessingFiles(new Map());
    setUploading(false);
    setFilesCollapsed(false);
    setExpandedFiles(new Set());
    successNotifiedRef.current.clear(); // Clear success notification records
  }, []);

  // Check if in processing state
  const isProcessing = uploading || processingFiles.size > 0;

  const FileTypeIcon: React.FC<{ type: FileType }> = ({ type }) => {
    const iconMap: Record<FileType, React.ReactNode> = {
      markdown: <FileText size={20} />,
      pdf: <File size={20} />,
      word: <BookOpen size={20} />,
      html: <Globe size={20} />,
      text: <FileCode size={20} />,
    };
    return <span className="file-icon">{iconMap[type] || <File size={20} />}</span>;
  };

  const toggleFileExpansion = (fileId: string) => {
    setExpandedFiles(prev => {
      const newSet = new Set(prev);
      if (newSet.has(fileId)) {
        newSet.delete(fileId);
      } else {
        newSet.add(fileId);
      }
      return newSet;
    });
  };

  const completedCount = Array.from(processingFiles.values()).filter(
    f => f.stage === ProcessingStage.COMPLETED
  ).length;
  const totalProcessing = processingFiles.size;

  return (
    <div className="file-upload-container">
      <h2>
        <Book size={20} style={{ display: 'inline', verticalAlign: 'middle', marginRight: '8px' }} />
        Upload Documents to Knowledge Base
      </h2>
      
      {/* File Drop Zone - only show when not processing */}
      {!isProcessing && (
        <div
          className={`drop-zone ${files.length > 0 ? 'has-files compact' : ''}`}
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
          <div className="drop-zone-icon">
            <File size={48} />
          </div>
          <p>Click to select files or drag and drop</p>
          <p className="drop-zone-hint">
            Supports: .md, .pdf, .docx, .html, .txt
          </p>
        </label>
      </div>
      )}

      {/* Selected Files - only show when not processing */}
      {files.length > 0 && !isProcessing && (
        <>
          <div className="section-divider"></div>
          <div className={`files-list ${filesCollapsed ? 'collapsed' : ''}`}>
            <div 
              className="files-list-header"
              onClick={() => setFilesCollapsed(!filesCollapsed)}
              style={{ cursor: 'pointer' }}
            >
              <h3>Selected Files ({files.length})</h3>
              <ChevronDown 
                size={18} 
                className={`collapse-icon ${filesCollapsed ? 'rotated' : ''}`}
              />
            </div>
            {!filesCollapsed && (
              <div className="files-grid">
                {files.map((file, index) => (
                  <div key={index} className="file-item">
                    <FileTypeIcon type={file.fileType} />
                    <div className="file-info">
                      <span className="file-name">{file.name || 'Unknown file'}</span>
                      <span className="file-size">{formatFileSize(file.size)}</span>
                    </div>
                    <button
                      className="remove-btn"
                      onClick={() => removeFile(index)}
                      disabled={uploading}
                      title="Remove file"
                    >
                      <X size={16} />
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>
        </>
      )}

      {/* Processing Files with Timeline */}
      {processingFiles.size > 0 && (
        <>
          <div className="section-divider"></div>
          <div className="processing-queue-section">
            <div className="processing-header">
              <h3>Processing Files ({totalProcessing})</h3>
              {totalProcessing > 0 && (
                <div className="processing-summary">
                  <span className="summary-text">
                    {completedCount} of {totalProcessing} completed
                  </span>
                  <div className="summary-progress-bar">
                    <div 
                      className="summary-progress-fill"
                      style={{ width: `${(completedCount / totalProcessing) * 100}%` }}
                    />
                  </div>
                </div>
              )}
            </div>
            <div className="processing-files-list">
              {Array.from(processingFiles.values()).map((fileStatus, index) => {
                const isExpanded = expandedFiles.has(fileStatus.id);
                return (
                  <div 
                    key={fileStatus.id || `file-${index}-${fileStatus.startTime || 0}`} 
                    className="processing-file-item"
                  >
                    <div 
                      className="file-header"
                      onClick={() => toggleFileExpansion(fileStatus.id)}
                      style={{ cursor: 'pointer' }}
                    >
                      <FileTypeIcon type={detectFileType(fileStatus.file?.name)} />
                      <div className="file-info">
                        <span className="file-name">{fileStatus.file?.name || 'Unknown file'}</span>
                        <span className={`status-badge ${fileStatus.stage}`}>
                          {fileStatus.stage === ProcessingStage.ERROR ? 'Failed' : 
                           fileStatus.stage === ProcessingStage.COMPLETED ? 'Completed' :
                           fileStatus.message}
                        </span>
                      </div>
                      <div className="file-actions">
                        {fileStatus.stage === ProcessingStage.ERROR && fileStatus.retryable && fileStatus.retryCount < 3 && (
                          <button 
                            className="retry-small-btn" 
                            onClick={(e) => {
                              e.stopPropagation();
                              handleRetry(fileStatus.id);
                            }}
                          >
                            Retry
                          </button>
                        )}
                        <button 
                          className="expand-btn"
                          onClick={(e) => {
                            e.stopPropagation();
                            toggleFileExpansion(fileStatus.id);
                          }}
                        >
                          {isExpanded ? <ChevronUp size={20} /> : <ChevronDown size={20} />}
                        </button>
                        <button 
                          className="remove-btn" 
                          onClick={(e) => {
                            e.stopPropagation();
                            removeProcessingFile(fileStatus.id);
                          }}
                          title="Remove"
                        >
                          <X size={16} />
                        </button>
                      </div>
                    </div>
                    {isExpanded && (
                      <div className="file-details">
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
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        </>
      )}

      {/* Sticky Action Bar */}
      {(files.length > 0 || isProcessing) && (
        <div className="upload-action-bar">
          <div className="action-bar-content">
            {isProcessing ? (
              <>
                <div className="processing-status-info">
                  <span className="status-text">
                    {completedCount} of {totalProcessing} completed
                  </span>
                  <div className="status-progress-bar">
                    <div 
                      className="status-progress-fill"
                      style={{ width: `${totalProcessing > 0 ? (completedCount / totalProcessing) * 100 : 0}%` }}
                    />
                  </div>
                </div>
                <button
                  className="clear-all-btn"
                  onClick={handleClearAll}
                  disabled={uploading}
                  title="Clear all and start new upload"
                >
                  New Upload
                </button>
              </>
            ) : (
              <>
                <span className="file-count">
                  {files.length} file{files.length !== 1 ? 's' : ''} selected
                </span>
                <button
                  className="upload-btn"
                  onClick={handleUpload}
                  disabled={files.length === 0 || uploading}
                >
                  {uploading ? 'Processing...' : `Upload ${files.length} File${files.length !== 1 ? 's' : ''}`}
                </button>
              </>
            )}
          </div>
        </div>
      )}

    </div>
  );
};
