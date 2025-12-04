import React, { useState, useEffect } from 'react';
import { ConfigPanel } from './components/ConfigPanel';
import { CollectionManager } from './components/CollectionManager';
import { FileUpload } from './components/FileUpload';
import { SourceFileManager } from './components/SourceFileManager';
import { ChunksViewer } from './components/ChunksViewer';
import type { AppConfig } from './types/config';
import { getDefaultConfig } from './types/config';
import { UploadResponse, BatchUploadResponse, updateApiClientUrl } from './api/client';
import './App.css';

function App() {
  const [config, setConfig] = useState<AppConfig>(() => {
    const saved = localStorage.getItem('kb-config');
    return saved ? JSON.parse(saved) : getDefaultConfig();
  });
  
  const [currentCollection, setCurrentCollection] = useState(config.defaultCollection);
  const [showSettings, setShowSettings] = useState(false);
  const [activeTab, setActiveTab] = useState<'upload' | 'sources' | 'chunks'>('upload');
  const [uploadResult, setUploadResult] = useState<UploadResponse | BatchUploadResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [selectedSource, setSelectedSource] = useState<string | null>(null);
  
  const handleViewChunks = (documentId: string) => {
    setSelectedSource(documentId);
    setActiveTab('chunks');
  };

  // Update API client URL when config changes
  useEffect(() => {
    localStorage.setItem('kb-config', JSON.stringify(config));
    updateApiClientUrl(config.apiUrl);
  }, [config]);

  const handleUploadSuccess = (result: UploadResponse | BatchUploadResponse) => {
    setUploadResult(result);
    setError(null);
  };

  const handleUploadError = (errorMessage: string) => {
    setError(errorMessage);
    setUploadResult(null);
  };

  return (
    <div className="app">
      <header className="app-header">
        <h1>Knowledge Base Builder</h1>
        <p>Upload documents to index into vector knowledge base</p>
        <button 
          onClick={() => setShowSettings(!showSettings)} 
          className="settings-btn"
        >
          ⚙️ {showSettings ? 'Hide Settings' : 'Settings'}
        </button>
      </header>

      <div className="app-layout">
        <aside className="sidebar">
          <CollectionManager
            currentCollection={currentCollection}
            onCollectionChange={setCurrentCollection}
          />
        </aside>

        <main className="main-content">
          {showSettings ? (
            <ConfigPanel
              config={config}
              onConfigChange={setConfig}
            />
          ) : (
            <>
              <div className="main-tabs">
                <button
                  className={activeTab === 'upload' ? 'active' : ''}
                  onClick={() => setActiveTab('upload')}
                >
                  📤 Upload Files
                </button>
                <button
                  className={activeTab === 'sources' ? 'active' : ''}
                  onClick={() => setActiveTab('sources')}
                >
                  📁 Source Files
                </button>
                {selectedSource && (
                  <button
                    className={activeTab === 'chunks' ? 'active' : ''}
                    onClick={() => setActiveTab('chunks')}
                  >
                    📄 Chunks
                  </button>
                )}
              </div>

              <div className="main-content-panel">
                {activeTab === 'upload' && (
                  <>
                    <div className="upload-section">
                      <FileUpload
                        config={config}
                        collection={currentCollection}
                        onUploadSuccess={handleUploadSuccess}
                        onUploadError={handleUploadError}
                      />
                    </div>

                    {error && (
                      <div className="error-message">
                        <h3>Error</h3>
                        <p>{error}</p>
                      </div>
                    )}

                    {uploadResult && (
                      <div className="success-message">
                        <h3>✅ Upload Successful!</h3>
                        {'chunks_indexed' in uploadResult ? (
                          <div>
                            <p><strong>File:</strong> {uploadResult.filename}</p>
                            <p><strong>Chunks Indexed:</strong> {uploadResult.chunks_indexed}</p>
                            <p><strong>Collection:</strong> {uploadResult.collection_name}</p>
                            <p><strong>Message:</strong> {uploadResult.message}</p>
                          </div>
                        ) : (
                          <div>
                            <p><strong>Total Files:</strong> {uploadResult.total_files}</p>
                            <ul>
                              {uploadResult.results.map((result, index) => (
                                <li key={index}>
                                  {result.filename}: {result.success ? 
                                    `✓ ${result.chunks_indexed} chunks` : 
                                    `✗ ${result.message}`}
                                </li>
                              ))}
                            </ul>
                          </div>
                        )}
                      </div>
                    )}
                  </>
                )}

                {activeTab === 'sources' && (
                  <SourceFileManager 
                    collectionName={currentCollection}
                    onViewChunks={handleViewChunks}
                    selectedSource={selectedSource}
                  />
                )}

                {activeTab === 'chunks' && selectedSource && (
                  <ChunksViewer
                    collectionName={currentCollection}
                    documentId={selectedSource}
                    onClose={() => {
                      setSelectedSource(null);
                      setActiveTab('sources');
                    }}
                  />
                )}
              </div>
            </>
          )}
        </main>
      </div>
    </div>
  );
}

export default App;
