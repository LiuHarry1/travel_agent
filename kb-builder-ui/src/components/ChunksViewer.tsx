import React, { useState, useEffect } from 'react';
import { apiClient, ChunksResponse } from '../api/client';
import { getLocationBadges, filterEmptyMetadata, formatMetadata } from '../utils/metadata';
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
  const [activeTab, setActiveTab] = useState<Record<number, string>>({});
  const [leftPanelWidth, setLeftPanelWidth] = useState(350);
  const [isResizing, setIsResizing] = useState(false);

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
      console.log('=== Backend Response ===');
      console.log('Loaded chunks data:', data);
      if (data && data.chunks && data.chunks.length > 0) {
        console.log('First chunk sample:', data.chunks[0]);
        console.log('First chunk metadata:', data.chunks[0].metadata);
        console.log('First chunk location:', data.chunks[0].location);
        console.log('First chunk keys:', Object.keys(data.chunks[0]));
        if (data.chunks[0].metadata) {
          console.log('Metadata keys:', Object.keys(data.chunks[0].metadata));
          console.log('Metadata values:', data.chunks[0].metadata);
        }
        console.log('First chunk location:', data.chunks[0].location);
      }
      setChunksData(data);
    } catch (err) {
      console.error('Failed to load chunks:', err);
    } finally {
      setLoadingChunks(false);
    }
  };

  const handleSelectChunk = (chunkIndex: number) => {
    setExpandedChunkId(chunkIndex);
    if (!activeTab[chunkIndex]) {
      setActiveTab({ ...activeTab, [chunkIndex]: 'text' });
    }
  };

  const handleTabChange = (chunkIndex: number, tab: string) => {
    setActiveTab({ ...activeTab, [chunkIndex]: tab });
  };

  // Resizer functionality
  const handleMouseDown = (e: React.MouseEvent) => {
    e.preventDefault();
    setIsResizing(true);
  };

  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      if (!isResizing) return;
      
      const container = document.querySelector('.chunks-layout') as HTMLElement;
      if (!container) return;
      
      const containerRect = container.getBoundingClientRect();
      const newWidth = e.clientX - containerRect.left;
      
      // 限制最小和最大宽度
      const minWidth = 250;
      const maxWidth = Math.min(600, containerRect.width * 0.6);
      
      if (newWidth >= minWidth && newWidth <= maxWidth) {
        setLeftPanelWidth(newWidth);
      }
    };

    const handleMouseUp = () => {
      setIsResizing(false);
    };

    if (isResizing) {
      document.addEventListener('mousemove', handleMouseMove);
      document.addEventListener('mouseup', handleMouseUp);
      document.body.style.cursor = 'col-resize';
      document.body.style.userSelect = 'none';
    }

    return () => {
      document.removeEventListener('mousemove', handleMouseMove);
      document.removeEventListener('mouseup', handleMouseUp);
      document.body.style.cursor = '';
      document.body.style.userSelect = '';
    };
  }, [isResizing]);

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
    <>
    <div className="chunks-viewer-container">
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

          <div className={`chunks-layout ${isResizing ? 'resizing' : ''}`}>
            <div 
              className="chunks-list-panel"
              style={{ width: `${leftPanelWidth}px`, flexShrink: 0 }}
            >
              <div className="chunks-list">
                {(searchQuery ? filteredChunks : chunksData.chunks).map((chunk) => {
                  const isSelectedChunk = expandedChunkId === chunk.index;
                  const displayIndex = chunk.index + 1;
                  return (
                    <div 
                      key={`chunk-${chunk.index}`} 
                      className={`chunk-list-item ${isSelectedChunk ? 'selected' : ''}`}
                      onClick={() => handleSelectChunk(chunk.index)}
                    >
                      <div className="chunk-list-item-header">
                        <span className="chunk-index">#{displayIndex}</span>
                        <span className="chunk-meta-info">
                          {chunk.text.length} chars
                        </span>
                      </div>
                      {chunk.location && getLocationBadges(chunk.location).length > 0 && (
                        <div className="chunk-location-badges">
                          {(() => {
                            const badges = getLocationBadges(chunk.location);
                            // Prioritize heading_path, then show page_number and others
                            const sortedBadges = badges.sort((a, b) => {
                              if (a.type === 'heading') return -1;
                              if (b.type === 'heading') return 1;
                              if (a.type === 'page') return -1;
                              if (b.type === 'page') return 1;
                              return 0;
                            });
                            return sortedBadges.slice(0, 3).map((badge, idx) => (
                              <span key={idx} className={`location-badge location-badge-${badge.type}`}>
                                {badge.label}: {badge.value}
                              </span>
                            ));
                          })()}
                        </div>
                      )}
                      <div className="chunk-list-item-preview">
                        {chunk.text.substring(0, 100)}{chunk.text.length > 100 ? '...' : ''}
                      </div>
                    </div>
                  );
                })}
                {searchQuery && filteredChunks.length === 0 && (
                  <div className="empty-state">No chunks match your search</div>
                )}
              </div>
            </div>
            
            <div 
              className="chunks-resizer"
              onMouseDown={handleMouseDown}
            />

            <div className="chunk-detail-panel">
              {expandedChunkId !== null ? (() => {
                const selectedChunk = (searchQuery ? filteredChunks : chunksData.chunks).find(
                  chunk => chunk.index === expandedChunkId
                );
                if (!selectedChunk) return <div className="empty-state">Chunk not found</div>;
                
                // Debug: Log selected chunk data
                console.log('=== Selected Chunk Debug ===');
                console.log('Selected chunk:', selectedChunk);
                console.log('Selected chunk metadata:', selectedChunk.metadata);
                console.log('Selected chunk location:', selectedChunk.location);
                if (selectedChunk.metadata) {
                  console.log('Metadata keys:', Object.keys(selectedChunk.metadata));
                  console.log('Metadata full object:', JSON.stringify(selectedChunk.metadata, null, 2));
                } else {
                  console.log('No metadata');
                }
                
                // Extract location from metadata if not directly available
                const chunkLocation = selectedChunk.location || (selectedChunk.metadata?.location);
                console.log('Extracted chunkLocation:', chunkLocation);
                
                return (
                  <div className="chunk-detail-content">
                    <div className="chunk-detail-header">
                      <h3>Chunk #{selectedChunk.index + 1}</h3>
                      <span className="chunk-meta-info">
                        {selectedChunk.text.length} chars
                      </span>
                    </div>
                    
                    <div className="chunk-tabs">
                      <button
                        className={`chunk-tab ${(activeTab[selectedChunk.index] || 'text') === 'text' ? 'active' : ''}`}
                        onClick={() => handleTabChange(selectedChunk.index, 'text')}
                      >
                        文本内容
                      </button>
                      {chunkLocation && (
                        <button
                          className={`chunk-tab ${activeTab[selectedChunk.index] === 'location' ? 'active' : ''}`}
                          onClick={() => handleTabChange(selectedChunk.index, 'location')}
                        >
                          位置信息
                        </button>
                      )}
                      {selectedChunk.metadata && Object.keys(filterEmptyMetadata(selectedChunk.metadata)).length > 0 && (
                        <button
                          className={`chunk-tab ${activeTab[selectedChunk.index] === 'metadata' ? 'active' : ''}`}
                          onClick={() => handleTabChange(selectedChunk.index, 'metadata')}
                        >
                          元数据
                        </button>
                      )}
                      <button
                        className={`chunk-tab ${activeTab[selectedChunk.index] === 'technical' ? 'active' : ''}`}
                        onClick={() => handleTabChange(selectedChunk.index, 'technical')}
                      >
                        技术信息
                      </button>
                    </div>
                    
                    <div className="chunk-tab-content">
                      {(activeTab[selectedChunk.index] || 'text') === 'text' && (
                        <div className="chunk-text-panel">
                          <div className="chunk-text">{selectedChunk.text}</div>
                        </div>
                      )}
                      
                      {activeTab[selectedChunk.index] === 'location' && chunkLocation && (
                        <div className="chunk-location-panel">
                          <div className="metadata-table">
                            {chunkLocation.start_char !== undefined && (
                              <div className="metadata-row">
                                <span className="metadata-label">起始字符:</span>
                                <span className="metadata-value">{chunkLocation.start_char}</span>
                              </div>
                            )}
                            {chunkLocation.end_char !== undefined && (
                              <div className="metadata-row">
                                <span className="metadata-label">结束字符:</span>
                                <span className="metadata-value">{chunkLocation.end_char}</span>
                              </div>
                            )}
                            {chunkLocation.page_number !== undefined && (
                              <div className="metadata-row">
                                <span className="metadata-label">页码:</span>
                                <span className="metadata-value">{chunkLocation.page_number}</span>
                              </div>
                            )}
                            {chunkLocation.page_bbox && (
                              <div className="metadata-row">
                                <span className="metadata-label">页面坐标:</span>
                                <span className="metadata-value">
                                  ({chunkLocation.page_bbox.x0}, {chunkLocation.page_bbox.y0}) - 
                                  ({chunkLocation.page_bbox.x1}, {chunkLocation.page_bbox.y1})
                                </span>
                              </div>
                            )}
                            {chunkLocation.paragraph_index !== undefined && (
                              <div className="metadata-row">
                                <span className="metadata-label">段落索引:</span>
                                <span className="metadata-value">{chunkLocation.paragraph_index}</span>
                              </div>
                            )}
                            {chunkLocation.section_index !== undefined && (
                              <div className="metadata-row">
                                <span className="metadata-label">章节索引:</span>
                                <span className="metadata-value">{chunkLocation.section_index}</span>
                              </div>
                            )}
                            {chunkLocation.heading_path && chunkLocation.heading_path.length > 0 && (
                              <div className="metadata-row">
                                <span className="metadata-label">标题路径:</span>
                                <span className="metadata-value">{chunkLocation.heading_path.join(' > ')}</span>
                              </div>
                            )}
                            {chunkLocation.code_block_index !== undefined && (
                              <div className="metadata-row">
                                <span className="metadata-label">代码块索引:</span>
                                <span className="metadata-value">{chunkLocation.code_block_index}</span>
                              </div>
                            )}
                            {chunkLocation.image_index !== undefined && (
                              <div className="metadata-row">
                                <span className="metadata-label">图片索引:</span>
                                <span className="metadata-value">{chunkLocation.image_index}</span>
                              </div>
                            )}
                            {chunkLocation.image_url && (
                              <div className="metadata-row">
                                <span className="metadata-label">图片URL:</span>
                                <span className="metadata-value">
                                  <a href={chunkLocation.image_url} target="_blank" rel="noopener noreferrer">
                                    {chunkLocation.image_url}
                                  </a>
                                </span>
                              </div>
                            )}
                            {chunkLocation.table_index !== undefined && (
                              <div className="metadata-row">
                                <span className="metadata-label">表格索引:</span>
                                <span className="metadata-value">{chunkLocation.table_index}</span>
                              </div>
                            )}
                            {chunkLocation.table_cell && (
                              <div className="metadata-row">
                                <span className="metadata-label">表格单元格:</span>
                                <span className="metadata-value">{chunkLocation.table_cell}</span>
                              </div>
                            )}
                          </div>
                        </div>
                      )}
                      
                      {activeTab[selectedChunk.index] === 'metadata' && selectedChunk.metadata && (
                        <div className="chunk-metadata-panel">
                          <div className="metadata-table">
                            {Object.entries(filterEmptyMetadata(selectedChunk.metadata)).map(([key, value]) => (
                              <div key={key} className="metadata-row">
                                <span className="metadata-label">{key}:</span>
                                <span className="metadata-value">
                                  {typeof value === 'object' ? (
                                    <pre className="metadata-json-inline">{formatMetadata(value as Record<string, any>)}</pre>
                                  ) : (
                                    String(value)
                                  )}
                                </span>
                              </div>
                            ))}
                            {Object.keys(filterEmptyMetadata(selectedChunk.metadata)).length === 0 && (
                              <div className="empty-state">No metadata available</div>
                            )}
                          </div>
                        </div>
                      )}
                      
                      {activeTab[selectedChunk.index] === 'technical' && (
                        <div className="chunk-technical-panel">
                          <div className="metadata-table">
                            <div className="metadata-row">
                              <span className="metadata-label">ID:</span>
                              <span className="metadata-value">{selectedChunk.id}</span>
                            </div>
                            {selectedChunk.chunk_id && String(selectedChunk.chunk_id) !== String(selectedChunk.id) && (
                              <div className="metadata-row">
                                <span className="metadata-label">Chunk ID:</span>
                                <span className="metadata-value">{selectedChunk.chunk_id}</span>
                              </div>
                            )}
                            <div className="metadata-row">
                              <span className="metadata-label">Document ID:</span>
                              <span className="metadata-value">{selectedChunk.document_id}</span>
                            </div>
                            <div className="metadata-row">
                              <span className="metadata-label">Chunk Index:</span>
                              <span className="metadata-value">{selectedChunk.index}</span>
                            </div>
                            {selectedChunk.file_path && (
                              <div className="metadata-row">
                                <span className="metadata-label">File Path:</span>
                                <span className="metadata-value">{selectedChunk.file_path}</span>
                              </div>
                            )}
                            <div className="metadata-row">
                              <span className="metadata-label">Text Length:</span>
                              <span className="metadata-value">{selectedChunk.text.length} characters</span>
                            </div>
                            
                            {/* Location Information */}
                            {chunkLocation && (
                              <>
                                {chunkLocation.page_number !== undefined && (
                                  <div className="metadata-row">
                                    <span className="metadata-label">页码:</span>
                                    <span className="metadata-value">{chunkLocation.page_number}</span>
                                  </div>
                                )}
                                {chunkLocation.start_char !== undefined && (
                                  <div className="metadata-row">
                                    <span className="metadata-label">起始字符:</span>
                                    <span className="metadata-value">{chunkLocation.start_char}</span>
                                  </div>
                                )}
                                {chunkLocation.end_char !== undefined && (
                                  <div className="metadata-row">
                                    <span className="metadata-label">结束字符:</span>
                                    <span className="metadata-value">{chunkLocation.end_char}</span>
                                  </div>
                                )}
                                {chunkLocation.heading_path && chunkLocation.heading_path.length > 0 && (
                                  <div className="metadata-row">
                                    <span className="metadata-label">标题路径:</span>
                                    <span className="metadata-value">{chunkLocation.heading_path.join(' > ')}</span>
                                  </div>
                                )}
                                {chunkLocation.paragraph_index !== undefined && (
                                  <div className="metadata-row">
                                    <span className="metadata-label">段落索引:</span>
                                    <span className="metadata-value">{chunkLocation.paragraph_index}</span>
                                  </div>
                                )}
                                {chunkLocation.section_index !== undefined && (
                                  <div className="metadata-row">
                                    <span className="metadata-label">章节索引:</span>
                                    <span className="metadata-value">{chunkLocation.section_index}</span>
                                  </div>
                                )}
                                {chunkLocation.code_block_index !== undefined && (
                                  <div className="metadata-row">
                                    <span className="metadata-label">代码块索引:</span>
                                    <span className="metadata-value">{chunkLocation.code_block_index}</span>
                                  </div>
                                )}
                                {chunkLocation.image_index !== undefined && (
                                  <div className="metadata-row">
                                    <span className="metadata-label">图片索引:</span>
                                    <span className="metadata-value">{chunkLocation.image_index}</span>
                                  </div>
                                )}
                                {chunkLocation.image_url && (
                                  <div className="metadata-row">
                                    <span className="metadata-label">图片URL:</span>
                                    <span className="metadata-value">
                                      <a href={chunkLocation.image_url} target="_blank" rel="noopener noreferrer">
                                        {chunkLocation.image_url}
                                      </a>
                                    </span>
                                  </div>
                                )}
                                {chunkLocation.table_index !== undefined && (
                                  <div className="metadata-row">
                                    <span className="metadata-label">表格索引:</span>
                                    <span className="metadata-value">{chunkLocation.table_index}</span>
                                  </div>
                                )}
                                {chunkLocation.table_cell && (
                                  <div className="metadata-row">
                                    <span className="metadata-label">表格单元格:</span>
                                    <span className="metadata-value">{chunkLocation.table_cell}</span>
                                  </div>
                                )}
                                {chunkLocation.page_bbox && (
                                  <div className="metadata-row">
                                    <span className="metadata-label">页面坐标:</span>
                                    <span className="metadata-value">
                                      ({chunkLocation.page_bbox.x0}, {chunkLocation.page_bbox.y0}) - 
                                      ({chunkLocation.page_bbox.x1}, {chunkLocation.page_bbox.y1})
                                    </span>
                                  </div>
                                )}
                              </>
                            )}
                            
                            {/* Chunk Metadata from document.metadata */}
                            {selectedChunk.metadata && (
                              <>
                                {selectedChunk.metadata.file_name && (
                                  <div className="metadata-row">
                                    <span className="metadata-label">File Name:</span>
                                    <span className="metadata-value">{selectedChunk.metadata.file_name}</span>
                                  </div>
                                )}
                                {selectedChunk.metadata.file_size !== undefined && (
                                  <div className="metadata-row">
                                    <span className="metadata-label">File Size:</span>
                                    <span className="metadata-value">{selectedChunk.metadata.file_size} bytes</span>
                                  </div>
                                )}
                                {selectedChunk.metadata.saved_source_path && (
                                  <div className="metadata-row">
                                    <span className="metadata-label">Saved Source Path:</span>
                                    <span className="metadata-value">{selectedChunk.metadata.saved_source_path}</span>
                                  </div>
                                )}
                                {selectedChunk.metadata.file_id && (
                                  <div className="metadata-row">
                                    <span className="metadata-label">File ID:</span>
                                    <span className="metadata-value">{selectedChunk.metadata.file_id}</span>
                                  </div>
                                )}
                                {selectedChunk.metadata.original_type && (
                                  <div className="metadata-row">
                                    <span className="metadata-label">Original Type:</span>
                                    <span className="metadata-value">{selectedChunk.metadata.original_type}</span>
                                  </div>
                                )}
                                {selectedChunk.metadata.pages_info !== undefined && (
                                  <div className="metadata-row">
                                    <span className="metadata-label">Total Pages:</span>
                                    <span className="metadata-value">{selectedChunk.metadata.pages_info}</span>
                                  </div>
                                )}
                                {selectedChunk.metadata.chunk_size !== undefined && (
                                  <div className="metadata-row">
                                    <span className="metadata-label">Chunk Size:</span>
                                    <span className="metadata-value">{selectedChunk.metadata.chunk_size} characters</span>
                                  </div>
                                )}
                                {selectedChunk.metadata.start_pos !== undefined && (
                                  <div className="metadata-row">
                                    <span className="metadata-label">Start Position:</span>
                                    <span className="metadata-value">{selectedChunk.metadata.start_pos}</span>
                                  </div>
                                )}
                                {selectedChunk.metadata.end_pos !== undefined && (
                                  <div className="metadata-row">
                                    <span className="metadata-label">End Position:</span>
                                    <span className="metadata-value">{selectedChunk.metadata.end_pos}</span>
                                  </div>
                                )}
                                {selectedChunk.metadata.page_number !== undefined && (
                                  <div className="metadata-row">
                                    <span className="metadata-label">Page Number (in metadata):</span>
                                    <span className="metadata-value">{selectedChunk.metadata.page_number}</span>
                                  </div>
                                )}
                                {/* PDF Metadata */}
                                {(selectedChunk.metadata.pdf_title || selectedChunk.metadata.title) && (
                                  <div className="metadata-row">
                                    <span className="metadata-label">PDF Title:</span>
                                    <span className="metadata-value">{selectedChunk.metadata.pdf_title || selectedChunk.metadata.title}</span>
                                  </div>
                                )}
                                {(selectedChunk.metadata.pdf_author || selectedChunk.metadata.author) && (
                                  <div className="metadata-row">
                                    <span className="metadata-label">PDF Author:</span>
                                    <span className="metadata-value">{selectedChunk.metadata.pdf_author || selectedChunk.metadata.author}</span>
                                  </div>
                                )}
                                {(selectedChunk.metadata.pdf_subject || selectedChunk.metadata.subject) && (
                                  <div className="metadata-row">
                                    <span className="metadata-label">PDF Subject:</span>
                                    <span className="metadata-value">{selectedChunk.metadata.pdf_subject || selectedChunk.metadata.subject}</span>
                                  </div>
                                )}
                                {(selectedChunk.metadata.pdf_creator || selectedChunk.metadata.creator) && (
                                  <div className="metadata-row">
                                    <span className="metadata-label">PDF Creator:</span>
                                    <span className="metadata-value">{selectedChunk.metadata.pdf_creator || selectedChunk.metadata.creator}</span>
                                  </div>
                                )}
                              </>
                            )}
                          </div>
                        </div>
                      )}
                    </div>
                    
                    <div className="chunk-footer">
                      <span>Full ID: {selectedChunk.id}</span>
                    </div>
                  </div>
                );
              })() : (
                <div className="empty-state">Select a chunk to view details</div>
              )}
            </div>
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
    </>
  );
};

