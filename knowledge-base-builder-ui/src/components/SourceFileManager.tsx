import React, { useState, useEffect } from 'react';
import { apiClient, SourceFile, ChunksResponse } from '../api/client';
import './SourceFileManager.css';

interface SourceFileManagerProps {
  collectionName: string;
}

export const SourceFileManager: React.FC<SourceFileManagerProps> = ({ collectionName }) => {
  const [sources, setSources] = useState<SourceFile[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedSource, setSelectedSource] = useState<string | null>(null);
  const [chunksData, setChunksData] = useState<ChunksResponse | null>(null);
  const [chunksPage, setChunksPage] = useState(1);
  const [loadingChunks, setLoadingChunks] = useState(false);

  useEffect(() => {
    if (collectionName) {
      loadSources();
    }
  }, [collectionName]);

  useEffect(() => {
    if (selectedSource) {
      loadChunks(selectedSource, chunksPage);
    }
  }, [selectedSource, chunksPage]);

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

  const loadChunks = async (documentId: string, page: number) => {
    if (!collectionName) return;
    
    setLoadingChunks(true);
    try {
      const data = await apiClient.getSourceChunks(collectionName, documentId, page, 10);
      setChunksData(data);
    } catch (err) {
      console.error('Failed to load chunks:', err);
    } finally {
      setLoadingChunks(false);
    }
  };

  const handleDelete = async (documentId: string) => {
    if (!confirm(`Are you sure you want to delete this source file and all its ${sources.find(s => s.document_id === documentId)?.chunk_count || 0} chunks? This action cannot be undone.`)) {
      return;
    }
    
    try {
      await apiClient.deleteSource(collectionName, documentId);
      await loadSources();
      if (selectedSource === documentId) {
        setSelectedSource(null);
        setChunksData(null);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to delete source');
      console.error('Failed to delete source:', err);
    }
  };

  const handleViewChunks = (documentId: string) => {
    setSelectedSource(documentId);
    setChunksPage(1);
  };

  const handleCloseChunks = () => {
    setSelectedSource(null);
    setChunksData(null);
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
        <button onClick={loadSources} className="refresh-btn" disabled={loading}>
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
            <div key={source.document_id} className="source-file-item">
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
                  👁️ View
                </button>
                <button
                  onClick={() => handleDelete(source.document_id)}
                  className="delete-btn"
                  title="Delete source file"
                >
                  🗑️ Delete
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {selectedSource && chunksData && (
        <div className="chunks-viewer-overlay" onClick={handleCloseChunks}>
          <div className="chunks-viewer" onClick={(e) => e.stopPropagation()}>
            <div className="chunks-viewer-header">
              <h4>Chunks: {chunksData.document_id.split('/').pop() || chunksData.document_id}</h4>
              <button onClick={handleCloseChunks} className="close-btn">×</button>
            </div>
            
            <div className="chunks-pagination-info">
              Page {chunksData.page} of {chunksData.total_pages} ({chunksData.total} total chunks)
            </div>

            {loadingChunks ? (
              <div className="loading">Loading chunks...</div>
            ) : (
              <>
                <div className="chunks-list">
                  {chunksData.chunks.map((chunk) => (
                    <div key={chunk.id} className="chunk-item">
                      <div className="chunk-header">
                        <span className="chunk-index">Chunk #{chunk.index + 1}</span>
                        <span className="chunk-id">ID: {chunk.id}</span>
                      </div>
                      <div className="chunk-text">{chunk.text}</div>
                      <div className="chunk-meta">
                        {chunk.text.length} characters
                      </div>
                    </div>
                  ))}
                </div>

                {chunksData.total_pages > 1 && (
                  <div className="chunks-pagination">
                    <button
                      onClick={() => setChunksPage(p => Math.max(1, p - 1))}
                      disabled={chunksPage === 1}
                      className="page-btn"
                    >
                      ← Previous
                    </button>
                    <span className="page-info">
                      Page {chunksData.page} / {chunksData.total_pages}
                    </span>
                    <button
                      onClick={() => setChunksPage(p => Math.min(chunksData.total_pages, p + 1))}
                      disabled={chunksPage === chunksData.total_pages}
                      className="page-btn"
                    >
                      Next →
                    </button>
                  </div>
                )}
              </>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

