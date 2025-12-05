import React, { useState, useEffect } from 'react';
import { apiClient } from '../api/client';
import { Collection } from '../types/collection';
import type { AppConfig, EmbeddingConfig } from '../types/config';
import { getEmbeddingDimension } from '../utils/embedding';
import './CollectionManager.css';

interface CollectionManagerProps {
  currentCollection: string;
  onCollectionChange: (name: string) => void;
  refreshTrigger?: number; // When this changes, refresh collections
  config?: AppConfig; // Optional config for embedding dimension
}

export const CollectionManager: React.FC<CollectionManagerProps> = ({
  currentCollection,
  onCollectionChange,
  refreshTrigger,
  config,
}) => {
  const [collections, setCollections] = useState<Collection[]>([]);
  const [loading, setLoading] = useState(false);
  const [showCreateDialog, setShowCreateDialog] = useState(false);
  const [newCollectionName, setNewCollectionName] = useState('');
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  
  // Embedding configuration for new collection
  const [embeddingConfig, setEmbeddingConfig] = useState<EmbeddingConfig>(() => {
    return config?.embedding || {
      provider: 'qwen',
      model: 'text-embedding-v2',
    };
  });

  // Update embedding config when global config changes
  useEffect(() => {
    if (config?.embedding) {
      setEmbeddingConfig(config.embedding);
    }
  }, [config]);

  useEffect(() => {
    loadCollections();
  }, []);

  // Refresh collections when refreshTrigger changes
  useEffect(() => {
    if (refreshTrigger !== undefined) {
      loadCollections();
    }
  }, [refreshTrigger]);

  const loadCollections = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await apiClient.listCollections();
      setCollections(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load collections');
      console.error('Failed to load collections:', err);
    } finally {
      setLoading(false);
    }
  };

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

  const handleCreate = async () => {
    if (!newCollectionName.trim()) return;
    
    setCreating(true);
    setError(null);
    try {
      const embeddingDim = getEmbeddingDimension(embeddingConfig);
      await apiClient.createCollection(newCollectionName.trim(), embeddingDim);
      setShowCreateDialog(false);
      setNewCollectionName('');
      // Reset to default config
      setEmbeddingConfig(config?.embedding || {
        provider: 'qwen',
        model: 'text-embedding-v2',
      });
      await loadCollections();
      onCollectionChange(newCollectionName.trim());
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create collection');
      console.error('Failed to create collection:', err);
    } finally {
      setCreating(false);
    }
  };

  const handleCloseDialog = () => {
    setShowCreateDialog(false);
    setNewCollectionName('');
    // Reset to default config
    setEmbeddingConfig(config?.embedding || {
      provider: 'qwen',
      model: 'text-embedding-v2',
    });
  };

  const handleDelete = async (name: string) => {
    if (!confirm(`Are you sure you want to delete collection "${name}"? This action cannot be undone.`)) {
      return;
    }
    
    try {
      await apiClient.deleteCollection(name);
      await loadCollections();
      if (currentCollection === name) {
        onCollectionChange(collections[0]?.name || 'knowledge_base');
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to delete collection');
      console.error('Failed to delete collection:', err);
    }
  };

  return (
    <div className="collection-manager">
      <div className="collection-header">
        <h3>Collections</h3>
        <div className="collection-header-actions">
          <button 
            onClick={loadCollections} 
            className="refresh-btn" 
            disabled={loading}
            title="Refresh collections"
          >
            {loading ? '⏳' : '🔄'}
          </button>
          <button onClick={() => setShowCreateDialog(true)} className="create-btn">
            + New
          </button>
        </div>
      </div>

      {error && (
        <div className="error-message">{error}</div>
      )}

      {showCreateDialog && (
        <div className="modal-overlay" onClick={handleCloseDialog}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <h3>Create New Collection</h3>
            
            <div className="form-group">
              <label>Collection Name:</label>
              <input
                type="text"
                value={newCollectionName}
                onChange={(e) => setNewCollectionName(e.target.value)}
                placeholder="Collection name"
                autoFocus
                onKeyPress={(e) => {
                  if (e.key === 'Enter' && !creating) {
                    handleCreate();
                  }
                }}
              />
            </div>

            <div className="form-group">
              <label>Embedding Provider:</label>
              <select
                value={embeddingConfig.provider}
                onChange={(e) => setEmbeddingConfig({
                  ...embeddingConfig,
                  provider: e.target.value as 'qwen' | 'openai' | 'bge',
                  model: undefined, // Reset model when provider changes
                  bgeApiUrl: e.target.value === 'bge' ? embeddingConfig.bgeApiUrl : undefined,
                })}
              >
                <option value="qwen">Qwen (DashScope)</option>
                <option value="openai">OpenAI</option>
                <option value="bge">BGE (API)</option>
              </select>
            </div>

            <div className="form-group">
              <label>Embedding Model:</label>
              <select
                value={embeddingConfig.model || ''}
                onChange={(e) => setEmbeddingConfig({
                  ...embeddingConfig,
                  model: e.target.value,
                })}
              >
                {getModelOptions(embeddingConfig.provider).map((opt) => (
                  <option key={opt.value} value={opt.value}>
                    {opt.label}
                  </option>
                ))}
              </select>
            </div>

            {embeddingConfig.provider === 'bge' && (
              <div className="form-group">
                <label>BGE API URL:</label>
                <input
                  type="text"
                  value={embeddingConfig.bgeApiUrl || ''}
                  onChange={(e) => setEmbeddingConfig({
                    ...embeddingConfig,
                    bgeApiUrl: e.target.value,
                  })}
                  placeholder="http://10.150.115.110:6000"
                />
                <small>Base URL for BGE embedding service</small>
              </div>
            )}

            <div className="form-group">
              <small style={{ color: '#666' }}>
                Embedding Dimension: <strong>{getEmbeddingDimension(embeddingConfig)}</strong>
              </small>
            </div>

            <div className="modal-actions">
              <button onClick={handleCreate} disabled={creating || !newCollectionName.trim()}>
                {creating ? 'Creating...' : 'Create'}
              </button>
              <button onClick={handleCloseDialog} disabled={creating}>
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}

      <div className="collection-list">
        {loading ? (
          <div className="loading">Loading...</div>
        ) : collections.length === 0 ? (
          <div className="empty-state">No collections found</div>
        ) : (
          collections.map((collection) => (
            <div
              key={collection.name}
              className={`collection-item ${
                collection.name === currentCollection ? 'active' : ''
              }`}
              onClick={() => onCollectionChange(collection.name)}
            >
              <div className="collection-info">
                <div className="collection-name">{collection.name}</div>
                <div className="collection-stats">
                  {collection.chunk_count} chunks
                </div>
              </div>
              <div className="collection-actions">
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    handleDelete(collection.name);
                  }}
                  className="delete-btn"
                  title="Delete collection"
                >
                  ×
                </button>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
};

