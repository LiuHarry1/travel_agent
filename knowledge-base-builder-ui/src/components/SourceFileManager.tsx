import React, { useState, useEffect, useMemo } from 'react';
import { File, Eye, Trash2, Inbox, Search, X as XIcon } from 'lucide-react';
import { apiClient, SourceFile } from '../api/client';
import { ConfirmDialog } from './ui/ConfirmDialog';
import { Skeleton } from './ui/Skeleton';
import './SourceFileManager.css';

interface SourceFileManagerProps {
  collectionName: string;
  database?: string;
  onViewChunks: (documentId: string) => void;
  selectedSource: string | null;
  onSourceDeleted?: () => void; // Callback when a source is deleted
}

export const SourceFileManager: React.FC<SourceFileManagerProps> = ({ 
  collectionName,
  database,
  onViewChunks,
  selectedSource,
  onSourceDeleted
}) => {
  const [sources, setSources] = useState<SourceFile[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [deleteConfirm, setDeleteConfirm] = useState<{ isOpen: boolean; documentId: string }>({ isOpen: false, documentId: '' });
  const [searchQuery, setSearchQuery] = useState('');

  useEffect(() => {
    if (collectionName) {
      loadSources();
    }
  }, [collectionName]);

  const loadSources = async () => {
    if (!collectionName) return;
    
    setLoading(true);
    setError(null);
    try {
      const data = await apiClient.listSources(collectionName, database);
      setSources(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load sources');
      console.error('Failed to load sources:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = (documentId: string) => {
    setDeleteConfirm({ isOpen: true, documentId });
  };

  const confirmDelete = async () => {
    const { documentId } = deleteConfirm;
    setDeleteConfirm({ isOpen: false, documentId: '' });
    
    try {
      await apiClient.deleteSource(collectionName, documentId, database);
      await loadSources();
      // Notify parent component to refresh collections
      if (onSourceDeleted) {
        onSourceDeleted();
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to delete source');
      console.error('Failed to delete source:', err);
    }
  };

  const handleViewChunks = (documentId: string) => {
    onViewChunks(documentId);
  };

  const handleViewFile = async (documentId: string) => {
    try {
      // Get the actual file URL from the backend
      const fileUrl = await apiClient.getSourceFileUrl(collectionName, documentId, database);
      // Open in new window/tab
      window.open(fileUrl, '_blank');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to open file');
      console.error('Failed to get file URL:', err);
    }
  };

  const filteredSources = useMemo(() => {
    if (!searchQuery.trim()) return sources;
    const query = searchQuery.toLowerCase();
    return sources.filter(source => 
      source.filename.toLowerCase().includes(query) ||
      source.document_id.toLowerCase().includes(query)
    );
  }, [sources, searchQuery]);

  if (!collectionName) {
    return (
      <div className="source-file-manager">
        <div className="empty-state">Please select a collection to view source files</div>
      </div>
    );
  }

  return (
    <div className="source-file-manager">
      <div className="source-file-header">
        <h3>Source Files</h3>
        <div style={{ display: 'flex', gap: 'var(--spacing-sm, 8px)', alignItems: 'center' }}>
          <div className="search-container">
            <Search size={16} className="search-icon" />
            <input
              type="text"
              className="search-input"
              placeholder="Search files..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
            />
            {searchQuery && (
              <button
                className="search-clear-btn"
                onClick={() => setSearchQuery('')}
                aria-label="Clear search"
              >
                <XIcon size={14} />
              </button>
            )}
          </div>
          <button 
            onClick={() => {
              loadSources();
              // Also refresh collections to sync chunk counts
              if (onSourceDeleted) {
                onSourceDeleted();
              }
            }} 
            className="refresh-btn" 
            disabled={loading}
            title="Refresh sources"
          >
          </button>
        </div>
      </div>

      {error && (
        <div className="error-message">{error}</div>
      )}

      {loading ? (
        <div className="source-file-list">
          {Array.from({ length: 3 }).map((_, index) => (
            <div key={index} className="source-file-item">
              <div className="source-file-info">
                <Skeleton width="60%" height={20} variant="text" />
                <Skeleton width="30%" height={16} variant="text" />
              </div>
              <div className="source-file-actions">
                <Skeleton width={100} height={32} variant="rectangular" />
                <Skeleton width={80} height={32} variant="rectangular" />
                <Skeleton width={80} height={32} variant="rectangular" />
              </div>
            </div>
          ))}
        </div>
      ) : filteredSources.length === 0 ? (
        <div className="empty-state">
          <Inbox size={48} style={{ opacity: 0.3, marginBottom: '16px' }} />
          <p style={{ margin: 0, fontWeight: 'var(--font-medium, 500)' }}>
            {searchQuery ? 'No files match your search' : 'No source files found'}
          </p>
          <p style={{ margin: '8px 0 0 0', fontSize: 'var(--text-sm, 14px)', color: 'var(--text-secondary, #666)' }}>
            {searchQuery ? 'Try a different search term' : 'Upload files to this collection to get started'}
          </p>
        </div>
      ) : (
        <div className="source-file-list">
          {filteredSources.map((source) => (
            <div 
              key={source.document_id} 
              className={`source-file-item ${selectedSource === source.document_id ? 'selected' : ''}`}
            >
              <div className="source-file-info">
                <div className="source-file-name" title={source.document_id}>
                  <File size={16} style={{ display: 'inline', verticalAlign: 'middle', marginRight: '8px' }} />
                  {source.filename}
                </div>
                <div className="source-file-meta">
                  {source.chunk_count} chunks
                </div>
              </div>
              <div className="source-file-actions">
                <button
                  onClick={() => handleViewFile(source.document_id)}
                  className="view-file-btn"
                  title="View source file in new window"
                >
                  <File size={16} className="btn-icon" />
                  <span className="btn-text">View File</span>
                </button>
                <button
                  onClick={() => handleViewChunks(source.document_id)}
                  className="view-btn"
                  title="View chunks"
                >
                  <Eye size={16} className="btn-icon" />
                  <span className="btn-text">View Chunks</span>
                </button>
                <button
                  onClick={() => handleDelete(source.document_id)}
                  className="delete-btn"
                  title="Delete source file"
                >
                  <Trash2 size={16} className="btn-icon" />
                  <span className="btn-text">Delete</span>
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      <ConfirmDialog
        isOpen={deleteConfirm.isOpen}
        title="Delete Source File"
        message={`Are you sure you want to delete this source file and all its ${sources.find(s => s.document_id === deleteConfirm.documentId)?.chunk_count || 0} chunks? This action cannot be undone.`}
        confirmText="Delete"
        cancelText="Cancel"
        variant="danger"
        onConfirm={confirmDelete}
        onCancel={() => setDeleteConfirm({ isOpen: false, documentId: '' })}
      />
    </div>
  );
};

