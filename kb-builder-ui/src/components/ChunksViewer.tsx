import React, { useState, useEffect } from 'react';
import { apiClient, ChunksResponse } from '../api/client';
import './ChunksViewer.css';

interface ChunksViewerProps {
  collectionName: string;
  documentId: string | null;
  database?: string;
  onClose: () => void;
}

export const ChunksViewer: React.FC<ChunksViewerProps> = ({ 
  collectionName, 
  documentId,
  database,
  onClose 
}) => {
  const [chunksData, setChunksData] = useState<ChunksResponse | null>(null);
  const [chunksPage, setChunksPage] = useState(1);
  const [loadingChunks, setLoadingChunks] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [expandedChunkId, setExpandedChunkId] = useState<number | null>(null);
  const [isExpanded, setIsExpanded] = useState(true);

  useEffect(() => {
    if (documentId) {
      setChunksPage(1);
      setSearchQuery('');
      setExpandedChunkId(null);
      loadChunks(documentId, 1);
    } else {
      setChunksData(null);
    }
  }, [documentId, collectionName, database]);

  useEffect(() => {
    if (documentId) {
      loadChunks(documentId, chunksPage);
    }
  }, [chunksPage]);

  const loadChunks = async (docId: string, page: number) => {
    if (!collectionName) return;
    
    setLoadingChunks(true);
    try {
      const data = await apiClient.getSourceChunks(collectionName, docId, page, 10, database);
      setChunksData(data);
    } catch (err) {
      console.error('Failed to load chunks:', err);
    } finally {
      setLoadingChunks(false);
    }
  };

  const handleToggleChunk = (chunkIndex: number) => {
    setExpandedChunkId(expandedChunkId === chunkIndex ? null : chunkIndex);
  };

  // Filter chunks based on search query and sort by index
  const filteredChunks = chunksData?.chunks
    .filter(chunk => 
      chunk.text.toLowerCase().includes(searchQuery.toLowerCase())
    )
    .sort((a, b) => a.index - b.index) || [];

  if (!documentId) {
    return (
      <div className="chunks-viewer-container">
        <div className="empty-state">No document selected</div>
      </div>
    );
  }

  return (
    <div className={`chunks-viewer-container ${isExpanded ? 'expanded' : ''}`}>
      <div className="chunks-viewer-header">
        <div className="chunks-viewer-title">
          <h4>
            {chunksData 
              ? chunksData.document_id.split('/').pop() || chunksData.document_id
              : 'Loading...'}
          </h4>
          {chunksData && (
            <span className="chunks-count-badge">
              {chunksData.total} chunks
            </span>
          )}
        </div>
        <div className="chunks-viewer-actions">
          <button 
            onClick={() => setIsExpanded(!isExpanded)} 
            className="expand-btn"
            title={isExpanded ? 'Collapse' : 'Expand'}
          >
            {isExpanded ? '⤓' : '⤢'}
          </button>
          <button onClick={onClose} className="close-btn" title="Close">×</button>
        </div>
      </div>

      {loadingChunks ? (
        <div className="loading">Loading chunks...</div>
      ) : chunksData ? (
        <>
          <div className="chunks-toolbar">
            <div className="search-box">
              <input
                type="text"
                placeholder="Search in chunks..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="search-input"
              />
              {searchQuery && (
                <button 
                  onClick={() => setSearchQuery('')} 
                  className="search-clear"
                  title="Clear search"
                >
                  ×
                </button>
              )}
            </div>
            <div className="chunks-pagination-info">
              {searchQuery ? (
                <>
                  Showing {filteredChunks.length} of {chunksData.total} chunks
                  {filteredChunks.length > 0 && ` (Page ${chunksData.page})`}
                </>
              ) : (
                <>
                  Showing {((chunksData.page - 1) * 10) + 1}-
                  {Math.min(chunksData.page * 10, chunksData.total)} of {chunksData.total} chunks
                </>
              )}
            </div>
          </div>

          <div className="chunks-list">
            {(searchQuery ? filteredChunks : chunksData.chunks).map((chunk) => {
              const isExpandedChunk = expandedChunkId === chunk.index;
              const displayIndex = chunk.index + 1;
              return (
                <div key={chunk.id} className={`chunk-item ${isExpandedChunk ? 'expanded' : ''}`}>
                  <div 
                    className="chunk-header" 
                    onClick={() => handleToggleChunk(chunk.index)}
                  >
                    <div className="chunk-header-left">
                      <span className="chunk-index">#{displayIndex}</span>
                      <span className="chunk-meta-info">
                        {chunk.text.length} chars
                      </span>
                    </div>
                    <div className="chunk-header-right">
                      <span className="chunk-id">ID: {String(chunk.id).slice(-8)}</span>
                      <button className="chunk-toggle-btn">
                        {isExpandedChunk ? '▼' : '▶'}
                      </button>
                    </div>
                  </div>
                  {isExpandedChunk && (
                    <div className="chunk-content">
                      <div className="chunk-text">{chunk.text}</div>
                      <div className="chunk-footer">
                        <span>Full ID: {chunk.id}</span>
                      </div>
                    </div>
                  )}
                </div>
              );
            })}
            {searchQuery && filteredChunks.length === 0 && (
              <div className="empty-state">No chunks match your search</div>
            )}
          </div>

          {chunksData.total_pages > 1 && (
            <div className="chunks-pagination">
              <button
                onClick={() => {
                  setChunksPage(p => Math.max(1, p - 1));
                  setExpandedChunkId(null);
                }}
                disabled={chunksPage === 1}
                className="page-btn"
              >
                ← Prev
              </button>
              <div className="page-info">
                <input
                  type="number"
                  min={1}
                  max={chunksData.total_pages}
                  value={chunksPage}
                  onChange={(e) => {
                    const page = parseInt(e.target.value);
                    if (page >= 1 && page <= chunksData.total_pages) {
                      setChunksPage(page);
                      setExpandedChunkId(null);
                    }
                  }}
                  className="page-input"
                />
                <span> / {chunksData.total_pages}</span>
              </div>
              <button
                onClick={() => {
                  setChunksPage(p => Math.min(chunksData.total_pages, p + 1));
                  setExpandedChunkId(null);
                }}
                disabled={chunksPage === chunksData.total_pages}
                className="page-btn"
              >
                Next →
              </button>
            </div>
          )}
        </>
      ) : (
        <div className="loading">Loading chunks...</div>
      )}
    </div>
  );
};

