import React, { useState } from 'react';
import type { AppConfig, EmbeddingConfig, ChunkingConfig } from '../types/config';
import './ConfigPanel.css';

interface ConfigPanelProps {
  config: AppConfig;
  onConfigChange: (config: AppConfig) => void;
}

export const ConfigPanel: React.FC<ConfigPanelProps> = ({
  config,
  onConfigChange,
}) => {
  const [activeTab, setActiveTab] = useState<'api' | 'embedding' | 'chunking'>('api');

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

const ApiConfigForm: React.FC<{
  apiUrl: string;
  onChange: (apiUrl: string) => void;
}> = ({ apiUrl, onChange }) => {
  const [testResult, setTestResult] = useState<{ success: boolean; message: string } | null>(null);
  const [testing, setTesting] = useState(false);

  const handleTestConnection = async () => {
    setTesting(true);
    setTestResult(null);
    try {
      const response = await fetch(`${apiUrl}/api/v1/health`);
      if (response.ok) {
        const data = await response.json();
        setTestResult({
          success: true,
          message: `Connected successfully! Service: ${data.service || 'unknown'}`,
        });
      } else {
        setTestResult({
          success: false,
          message: `Server returned status ${response.status}`,
        });
      }
    } catch (error) {
      setTestResult({
        success: false,
        message: error instanceof Error ? error.message : 'Connection failed',
      });
    } finally {
      setTesting(false);
    }
  };

  return (
    <div className="api-config">
      <div className="form-group">
        <label>Backend API URL:</label>
        <input
          type="text"
          value={apiUrl}
          onChange={(e) => onChange(e.target.value)}
          placeholder="http://localhost:8001"
          className="api-url-input"
        />
        <p className="form-hint">
          Enter the base URL of your knowledge-base-builder backend API
        </p>
      </div>
      
      <div className="form-group">
        <button 
          onClick={handleTestConnection} 
          disabled={testing || !apiUrl} 
          className="test-btn"
        >
          {testing ? 'Testing...' : 'Test Connection'}
        </button>
      </div>
      
      {testResult && (
        <div className={`test-result ${testResult.success ? 'success' : 'error'}`}>
          {testResult.success ? '✓' : '✗'} {testResult.message}
        </div>
      )}
      
      <div className="config-info">
        <h4>Common API URLs:</h4>
        <ul>
          <li>Local development: <code>http://localhost:8001</code></li>
          <li>Production: <code>https://your-domain.com</code></li>
          <li>Docker: <code>http://localhost:8001</code> (if port is mapped)</li>
        </ul>
        <p className="form-hint">
          The API URL is saved in your browser's local storage and will persist across sessions.
        </p>
      </div>
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
          { value: 'BAAI/bge-large-en-v1.5', label: 'bge-large-en-v1.5 (1024d, English)' },
          { value: 'BAAI/bge-base-en-v1.5', label: 'bge-base-en-v1.5 (768d, English)' },
          { value: 'BAAI/bge-small-en-v1.5', label: 'bge-small-en-v1.5 (384d, English)' },
          { value: 'BAAI/bge-large-zh-v1.5', label: 'bge-large-zh-v1.5 (1024d, Chinese)' },
          { value: 'BAAI/bge-base-zh-v1.5', label: 'bge-base-zh-v1.5 (768d, Chinese)' },
          { value: 'BAAI/bge-small-zh-v1.5', label: 'bge-small-zh-v1.5 (384d, Chinese)' },
          { value: 'nvidia/llama-nemotron-embed-1b-v2', label: 'llama-nemotron-embed-1b-v2 (1024d)' },
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
          <option value="bge">BGE (API)</option>
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
      
      {config.provider === 'bge' && (
        <div className="form-group">
          <label>BGE API URL:</label>
          <input
            type="text"
            value={config.bgeApiUrl || ''}
            onChange={(e) => onChange({ ...config, bgeApiUrl: e.target.value })}
            placeholder="http://10.150.115.110:6000"
          />
          <small>Base URL for BGE embedding service (e.g., http://10.150.115.110:6000 for English, :6001 for Chinese)</small>
        </div>
      )}
      
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
  const estimatedChunks = (_size: number) => {
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

