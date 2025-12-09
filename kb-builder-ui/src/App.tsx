import { useState, useEffect } from 'react';
import { Settings, Upload, Folder, File } from 'lucide-react';
import { ConfigPanel } from './components/ConfigPanel';
import { CollectionManager } from './components/CollectionManager';
import { DatabaseManager } from './components/DatabaseManager';
import { FileUpload } from './components/FileUpload';
import { SourceFileManager } from './components/SourceFileManager';
import { ChunksViewer } from './components/ChunksViewer';
import { ToastContainer, useToast } from './components/ui/Toast';
import type { AppConfig } from './types/config';
import { getDefaultConfig } from './types/config';
import { UploadResponse, BatchUploadResponse, updateApiClientUrl } from './api/client';
import './App.css';

function App() {
  const toast = useToast();
  const [config, setConfig] = useState<AppConfig>(() => {
    const saved = localStorage.getItem('kb-config');
    return saved ? JSON.parse(saved) : getDefaultConfig();
  });
  
  const [currentDatabase, setCurrentDatabase] = useState<string>('default');
  const [currentCollection, setCurrentCollection] = useState(config.defaultCollection);
  const [showSettings, setShowSettings] = useState(false);
  const [activeTab, setActiveTab] = useState<'upload' | 'sources' | 'chunks'>('upload');
  const [selectedSource, setSelectedSource] = useState<string | null>(null);
  const [collectionRefreshTrigger, setCollectionRefreshTrigger] = useState(0);
  
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
    if ('chunks_indexed' in result) {
      toast.success(`File "${result.filename}" uploaded successfully! ${result.chunks_indexed} chunks indexed.`);
    } else {
      const successCount = result.results.filter(r => r.success).length;
      toast.success(`Batch upload completed! ${successCount}/${result.total_files} files processed successfully.`);
    }
    // Refresh collections to update chunk counts after successful upload
    setCollectionRefreshTrigger(prev => prev + 1);
  };

  const handleUploadError = (errorMessage: string) => {
    toast.error(errorMessage);
  };

  return (
    <div className="app">
      <ToastContainer toasts={toast.toasts} onDismiss={toast.dismissToast} />
      <header className="app-header">
        <h1>Knowledge Base Builder</h1>
        <p>Upload documents to index into vector knowledge base</p>
        <button 
          onClick={() => setShowSettings(!showSettings)} 
          className="settings-btn"
        >
          <Settings size={18} />
          {showSettings ? 'Hide Settings' : 'Settings'}
        </button>
      </header>

      <div className="app-layout">
        <aside className="sidebar">
          <DatabaseManager
            currentDatabase={currentDatabase}
            onDatabaseChange={setCurrentDatabase}
          />
          <CollectionManager
            currentCollection={currentCollection}
            onCollectionChange={setCurrentCollection}
            refreshTrigger={collectionRefreshTrigger}
            config={config}
            database={currentDatabase}
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
                  <Upload size={18} />
                  Upload Files
                </button>
                <button
                  className={activeTab === 'sources' ? 'active' : ''}
                  onClick={() => setActiveTab('sources')}
                >
                  <Folder size={18} />
                  Source Files
                </button>
                {selectedSource && (
                  <button
                    className={activeTab === 'chunks' ? 'active' : ''}
                    onClick={() => setActiveTab('chunks')}
                  >
                    <File size={18} />
                    Chunks
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
                        database={currentDatabase}
                        onUploadSuccess={handleUploadSuccess}
                        onUploadError={handleUploadError}
                      />
                    </div>
                  </>
                )}

                {activeTab === 'sources' && (
                  <SourceFileManager 
                    collectionName={currentCollection}
                    database={currentDatabase}
                    onViewChunks={handleViewChunks}
                    selectedSource={selectedSource}
                    onSourceDeleted={() => {
                      // Trigger collection refresh to update chunk counts
                      setCollectionRefreshTrigger(prev => prev + 1);
                    }}
                  />
                )}

                {activeTab === 'chunks' && selectedSource && (
                  <ChunksViewer
                    collectionName={currentCollection}
                    documentId={selectedSource}
                    database={currentDatabase}
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
