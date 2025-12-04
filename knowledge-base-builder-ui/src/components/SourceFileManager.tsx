import React, { useState, useEffect } from 'react';
import { apiClient, SourceFile } from '../api/client';
import './SourceFileManager.css';

interface SourceFileManagerProps {
  collectionName: string;
  onViewChunks: (documentId: string) => void;
  selectedSource: string | null;
  onSourceDeleted?: () => void; // Callback when a source is deleted
}

export const SourceFileManager: React.FC<SourceFileManagerProps> = ({ 
  collectionName, 
  onViewChunks,
  selectedSource,
  onSourceDeleted
}) => {
  const [sources, setSources] = useState<SourceFile[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

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
      const data = await apiClient.listSources(collectionName);
      setSources(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load sources');
      console.error('Failed to load sources:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async (documentId: string) => {
    if (!confirm(`Are you sure you want to delete this source file and all its ${sources.find(s => s.document_id === documentId)?.chunk_count || 0} chunks? This action cannot be undone.`)) {
      return;
    }
    
    try {
      await apiClient.deleteSource(collectionName, documentId);
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
        >
          {loading ? 'Loading...' : '🔄 Refresh'}
        </button>
      </div>

      {error && (
        <div className="error-message">{error}</div>
      )}

      {loading ? (
        <div className="loading">Loading sources...</div>
      ) : sources.length === 0 ? (
        <div className="empty-state">No source files found in this collection</div>
      ) : (
        <div className="source-file-list">
          {sources.map((source) => (
            <div 
              key={source.document_id} 
              className={`source-file-item ${selectedSource === source.document_id ? 'selected' : ''}`}
            >
              <div className="source-file-info">
                <div className="source-file-name" title={source.document_id}>
                  📄 {source.filename}
                </div>
                <div className="source-file-meta">
                  {source.chunk_count} chunks
                </div>
              </div>
              <div className="source-file-actions">
                <button
                  onClick={() => handleViewChunks(source.document_id)}
                  className="view-btn"
                  title="View chunks"
                >
                  <span className="btn-icon">👁</span>
                  <span className="btn-text">View</span>
                </button>
                <button
                  onClick={() => handleDelete(source.document_id)}
                  className="delete-btn"
                  title="Delete source file"
                >
                  <span className="btn-icon">🗑</span>
                  <span className="btn-text">Delete</span>
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

