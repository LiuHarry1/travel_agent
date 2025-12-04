import React, { useState } from 'react';
import type { AppConfig, MilvusConfig, EmbeddingConfig, ChunkingConfig } from '../types/config';
import { apiClient } from '../api/client';
import './ConfigPanel.css';

interface ConfigPanelProps {
  config: AppConfig;
  onConfigChange: (config: AppConfig) => void;
}

export const ConfigPanel: React.FC<ConfigPanelProps> = ({
  config,
  onConfigChange,
}) => {
  const [activeTab, setActiveTab] = useState<'api' | 'milvus' | 'embedding' | 'chunking'>('api');
  const [testing, setTesting] = useState(false);
  const [testResult, setTestResult] = useState<{ success: boolean; message: string } | null>(null);

  const handleTestConnection = async () => {
    setTesting(true);
    setTestResult(null);
    try {
      const result = await apiClient.testMilvusConnection(config.milvus);
      setTestResult(result);
    } catch (error) {
      setTestResult({
        success: false,
        message: error instanceof Error ? error.message : 'Connection test failed',
      });
    } finally {
      setTesting(false);
    }
  };

  return (
    <div className="config-panel">
      <div className="config-tabs" data-active-tab={activeTab}>
        <button
          className={activeTab === 'api' ? 'active' : ''}
          onClick={() => setActiveTab('api')}
        >
          API Settings
        </button>
        <button
          className={activeTab === 'milvus' ? 'active' : ''}
          onClick={() => setActiveTab('milvus')}
        >
          Milvus Connection
        </button>
        <button
          className={activeTab === 'embedding' ? 'active' : ''}
          onClick={() => setActiveTab('embedding')}
        >
          Embedding
        </button>
        <button
          className={activeTab === 'chunking' ? 'active' : ''}
          onClick={() => setActiveTab('chunking')}
        >
          Chunking
        </button>
      </div>

      <div className="config-content">
        {activeTab === 'api' && (
          <ApiConfigForm
            apiUrl={config.apiUrl}
            onChange={(apiUrl) => onConfigChange({ ...config, apiUrl })}
          />
        )}
        
        {activeTab === 'milvus' && (
          <MilvusConfigForm
            config={config.milvus}
            onChange={(milvus) => onConfigChange({ ...config, milvus })}
            onTest={handleTestConnection}
            testing={testing}
            testResult={testResult}
          />
        )}
        
        {activeTab === 'embedding' && (
          <EmbeddingConfigForm
            config={config.embedding}
            onChange={(embedding) => onConfigChange({ ...config, embedding })}
          />
        )}
        
        {activeTab === 'chunking' && (
          <ChunkingConfigForm
            config={config.chunking}
            onChange={(chunking) => onConfigChange({ ...config, chunking })}
          />
        )}
      </div>
    </div>
  );
};

const MilvusConfigForm: React.FC<{
  config: MilvusConfig;
  onChange: (config: MilvusConfig) => void;
  onTest: () => Promise<void>;
  testing: boolean;
  testResult: { success: boolean; message: string } | null;
}> = ({ config, onChange, onTest, testing, testResult }) => {
  return (
    <div className="milvus-config">
      <div className="form-group">
        <label>Host:</label>
        <input
          type="text"
          value={config.host}
          onChange={(e) => onChange({ ...config, host: e.target.value })}
          placeholder="localhost"
        />
      </div>
      
      <div className="form-group">
        <label>Port:</label>
        <input
          type="number"
          value={config.port}
          onChange={(e) => onChange({ ...config, port: parseInt(e.target.value) || 19530 })}
          placeholder="19530"
        />
      </div>
      
      <div className="form-group">
        <label>User (optional):</label>
        <input
          type="text"
          value={config.user || ''}
          onChange={(e) => onChange({ ...config, user: e.target.value || undefined })}
        />
      </div>
      
      <div className="form-group">
        <label>Password (optional):</label>
        <input
          type="password"
          value={config.password || ''}
          onChange={(e) => onChange({ ...config, password: e.target.value || undefined })}
        />
      </div>
      
      <button onClick={onTest} disabled={testing} className="test-btn">
        {testing ? 'Testing...' : 'Test Connection'}
      </button>
      
      {testResult && (
        <div className={`test-result ${testResult.success ? 'success' : 'error'}`}>
          {testResult.message}
        </div>
      )}
    </div>
  );
};

const EmbeddingConfigForm: React.FC<{
  config: EmbeddingConfig;
  onChange: (config: EmbeddingConfig) => void;
}> = ({ config, onChange }) => {
  const getModelOptions = (provider: string) => {
    switch (provider) {
      case 'qwen':
        return [
          { value: 'text-embedding-v2', label: 'text-embedding-v2 (1536d)' },
          { value: 'text-embedding-v1', label: 'text-embedding-v1 (1536d)' },
        ];
      case 'openai':
        return [
          { value: 'text-embedding-3-small', label: 'text-embedding-3-small (1536d)' },
          { value: 'text-embedding-3-large', label: 'text-embedding-3-large (3072d)' },
          { value: 'text-embedding-ada-002', label: 'text-embedding-ada-002 (1536d)' },
        ];
      case 'bge':
        return [
          { value: 'BAAI/bge-large-en-v1.5', label: 'bge-large-en-v1.5 (1024d)' },
          { value: 'BAAI/bge-base-en-v1.5', label: 'bge-base-en-v1.5 (768d)' },
          { value: 'BAAI/bge-small-en-v1.5', label: 'bge-small-en-v1.5 (384d)' },
        ];
      default:
        return [];
    }
  };

  return (
    <div className="embedding-config">
      <div className="form-group">
        <label>Provider:</label>
        <select
          value={config.provider}
          onChange={(e) => onChange({ ...config, provider: e.target.value as any, model: undefined })}
        >
          <option value="qwen">Qwen (DashScope)</option>
          <option value="openai">OpenAI</option>
          <option value="bge">BGE (Local)</option>
        </select>
      </div>
      
      <div className="form-group">
        <label>Model:</label>
        <select
          value={config.model || ''}
          onChange={(e) => onChange({ ...config, model: e.target.value })}
        >
          {getModelOptions(config.provider).map((opt) => (
            <option key={opt.value} value={opt.value}>
              {opt.label}
            </option>
          ))}
        </select>
      </div>
      
      {(config.provider === 'qwen' || config.provider === 'openai') && (
        <div className="form-group">
          <label>API Key (for testing):</label>
          <input
            type="password"
            value={config.apiKey || ''}
            onChange={(e) => onChange({ ...config, apiKey: e.target.value })}
            placeholder="Enter API key to test connection"
          />
          <small>API key is not stored, only used for testing</small>
        </div>
      )}
    </div>
  );
};

const ChunkingConfigForm: React.FC<{
  config: ChunkingConfig;
  onChange: (config: ChunkingConfig) => void;
}> = ({ config, onChange }) => {
  const estimatedChunks = (size: number) => {
    if (config.chunkSize <= config.chunkOverlap) return 0;
    return Math.ceil(10000 / (config.chunkSize - config.chunkOverlap));
  };

  return (
    <div className="chunking-config">
      <div className="form-group">
        <label>Strategy:</label>
        <select
          value={config.strategy}
          onChange={(e) => onChange({ ...config, strategy: e.target.value as any })}
        >
          <option value="recursive">Recursive (Recommended)</option>
          <option value="semantic">Semantic (Future)</option>
          <option value="fixed">Fixed Size</option>
        </select>
      </div>
      
      <div className="form-group">
        <label>Chunk Size:</label>
        <input
          type="number"
          value={config.chunkSize}
          onChange={(e) => onChange({ ...config, chunkSize: parseInt(e.target.value) || 1000 })}
          min={100}
          max={10000}
        />
        <small>Characters per chunk</small>
      </div>
      
      <div className="form-group">
        <label>Chunk Overlap:</label>
        <input
          type="number"
          value={config.chunkOverlap}
          onChange={(e) => onChange({ ...config, chunkOverlap: parseInt(e.target.value) || 200 })}
          min={0}
          max={1000}
        />
        <small>Overlapping characters between chunks</small>
      </div>
      
      <div className="preview-info">
        <p>Preview: With chunk size {config.chunkSize} and overlap {config.chunkOverlap},</p>
        <p>a 10,000 character document will create approximately {estimatedChunks(10000)} chunks.</p>
      </div>
    </div>
  );
};

