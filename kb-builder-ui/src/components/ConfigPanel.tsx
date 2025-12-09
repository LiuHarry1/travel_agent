import React, { useState } from 'react';
import { Lightbulb } from 'lucide-react';
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
  const [activeTab, setActiveTab] = useState<'embedding' | 'chunking'>('embedding');

  return (
    <div className="config-panel">
      <div className="config-tabs" data-active-tab={activeTab}>
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
        ];
      case 'bge-en':
        return [
          { value: 'BAAI/bge-large-en-v1.5', label: 'bge-large-en-v1.5 (1024d)' },
          { value: 'BAAI/bge-base-en-v1.5', label: 'bge-base-en-v1.5 (768d)' },
          { value: 'BAAI/bge-small-en-v1.5', label: 'bge-small-en-v1.5 (384d)' },
        ];
      case 'bge-zh':
        return [
          { value: 'BAAI/bge-large-zh-v1.5', label: 'bge-large-zh-v1.5 (1024d)' },
          { value: 'BAAI/bge-base-zh-v1.5', label: 'bge-base-zh-v1.5 (768d)' },
          { value: 'BAAI/bge-small-zh-v1.5', label: 'bge-small-zh-v1.5 (384d)' },
        ];
      case 'nemotron':
      case 'nvidia':
        return [
          { value: 'nvidia/llama-nemotron-embed-1b-v2', label: 'llama-nemotron-embed-1b-v2 (1024d)' },
        ];
      case 'snowflake':
        return [
          { value: 'Snowflake/snowflake-arctic-embed-l', label: 'snowflake-arctic-embed-l (1024d)' },
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
          <option value="bge">BGE (General API)</option>
          <option value="bge-en">BGE English (API)</option>
          <option value="bge-zh">BGE Chinese (API)</option>
          <option value="nemotron">NVIDIA Nemotron (API)</option>
          <option value="nvidia">NVIDIA (Alias for Nemotron)</option>
          <option value="snowflake">Snowflake Arctic (API)</option>
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
            placeholder="http://localhost:8001"
          />
          <small>Base URL for BGE embedding service (general BGE API)</small>
        </div>
      )}
      
      {config.provider === 'bge-en' && (
        <div className="form-group">
          <label>BGE English API URL:</label>
          <input
            type="text"
            value={config.bgeEnApiUrl || ''}
            onChange={(e) => onChange({ ...config, bgeEnApiUrl: e.target.value })}
            placeholder="http://10.150.115.110:6000"
          />
          <small>Base URL for English BGE embedding service</small>
        </div>
      )}
      
      {config.provider === 'bge-zh' && (
        <div className="form-group">
          <label>BGE Chinese API URL:</label>
          <input
            type="text"
            value={config.bgeZhApiUrl || ''}
            onChange={(e) => onChange({ ...config, bgeZhApiUrl: e.target.value })}
            placeholder="http://10.150.115.110:6001"
          />
          <small>Base URL for Chinese BGE embedding service</small>
        </div>
      )}
      
      {(config.provider === 'nemotron' || config.provider === 'nvidia') && (
        <div className="form-group">
          <label>Nemotron API URL:</label>
          <input
            type="text"
            value={config.nemotronApiUrl || ''}
            onChange={(e) => onChange({ ...config, nemotronApiUrl: e.target.value })}
            placeholder="http://10.150.115.110:6002/embed"
          />
          <small>Full API endpoint URL for NVIDIA Nemotron embedding service</small>
        </div>
      )}
      
      {config.provider === 'snowflake' && (
        <div className="form-group">
          <label>Snowflake API URL:</label>
          <input
            type="text"
            value={config.snowflakeApiUrl || ''}
            onChange={(e) => onChange({ ...config, snowflakeApiUrl: e.target.value })}
            placeholder="http://10.150.115.110:6003/embed"
          />
          <small>Full API endpoint URL for Snowflake Arctic embedding service</small>
        </div>
      )}
      
      {(config.provider === 'qwen' || config.provider === 'openai') && (
        <>
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
          {config.provider === 'openai' && (
            <div className="form-group">
              <label>OpenAI Base URL (optional):</label>
              <input
                type="text"
                value={config.openaiBaseUrl || ''}
                onChange={(e) => onChange({ ...config, openaiBaseUrl: e.target.value })}
                placeholder="https://api.openai.com/v1"
              />
              <small>Custom base URL for OpenAI-compatible API (e.g., for proxy or custom endpoints)</small>
            </div>
          )}
        </>
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
        <Lightbulb size={16} style={{ position: 'absolute', top: 'var(--spacing-sm)', right: 'var(--spacing-sm)', opacity: 0.3 }} />
        <p>Preview: With chunk size {config.chunkSize} and overlap {config.chunkOverlap},</p>
        <p>a 10,000 character document will create approximately {estimatedChunks(10000)} chunks.</p>
      </div>
    </div>
  );
};

