import React, { useState, useEffect, useMemo, useCallback, useRef } from 'react';
import { Folder, BarChart3, Inbox, Sparkles, Search, X as XIcon } from 'lucide-react';
import { apiClient } from '../api/client';
import { Collection } from '../types/collection';
import type { AppConfig, EmbeddingConfig } from '../types/config';
import { getEmbeddingDimension } from '../utils/embedding';
import { ConfirmDialog } from './ui/ConfirmDialog';
import { Skeleton } from './ui/Skeleton';
import './CollectionManager.css';

interface CollectionManagerProps {
  currentCollection: string;
  onCollectionChange: (name: string) => void;
  refreshTrigger?: number; // When this changes, refresh collections
  config?: AppConfig; // Optional config for embedding dimension
  database?: string; // Current database name
}

export const CollectionManager: React.FC<CollectionManagerProps> = ({
  currentCollection,
  onCollectionChange,
  refreshTrigger,
  config,
  database = 'default',
}) => {
  const [collections, setCollections] = useState<Collection[]>([]);
  const [loading, setLoading] = useState(false);
  const [showCreateDialog, setShowCreateDialog] = useState(false);
  const [newCollectionName, setNewCollectionName] = useState('');
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [deleteConfirm, setDeleteConfirm] = useState<{ isOpen: boolean; name: string }>({ isOpen: false, name: '' });
  const [searchQuery, setSearchQuery] = useState('');
  const loadingRef = useRef(false);
  
  // 排序函数：按创建时间排序，如果相同则按名称排序
  const sortCollections = useCallback((data: Collection[]): Collection[] => {
    return [...data].sort((a, b) => {
      const timeA = a.created_at ? new Date(a.created_at).getTime() : 0;
      const timeB = b.created_at ? new Date(b.created_at).getTime() : 0;
      
      if (timeA > 0 && timeB > 0 && timeA !== timeB) {
        return timeA - timeB; // 升序：最早创建的在前
      }
      
      // 如果创建时间相同或无效，按名称排序以保持稳定的顺序
      return a.name.localeCompare(b.name, undefined, { numeric: true, sensitivity: 'base' });
    });
  }, []);
  
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

  const loadCollections = useCallback(async () => {
    // 防止重复加载
    if (loadingRef.current) return;
    
    loadingRef.current = true;
    setLoading(true);
    setError(null);
    try {
      const data = await apiClient.listCollections(database);
      // 使用统一的排序函数确保排序稳定
      const sortedData = sortCollections(data);
      setCollections(sortedData);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load collections');
      console.error('Failed to load collections:', err);
    } finally {
      setLoading(false);
      loadingRef.current = false;
    }
  }, [database, sortCollections]);

  // Load collections when database changes or refreshTrigger changes
  useEffect(() => {
    loadCollections();
  }, [database, refreshTrigger, loadCollections]);

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
      await apiClient.createCollection(newCollectionName.trim(), embeddingDim, database);
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

  const handleDelete = (name: string) => {
    setDeleteConfirm({ isOpen: true, name });
  };

  const confirmDelete = async () => {
    const { name } = deleteConfirm;
    setDeleteConfirm({ isOpen: false, name: '' });
    
    try {
      await apiClient.deleteCollection(name, database);
      await loadCollections();
      if (currentCollection === name) {
        onCollectionChange(collections[0]?.name || 'knowledge_base');
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to delete collection');
      console.error('Failed to delete collection:', err);
    }
  };

  const filteredCollections = useMemo(() => {
    if (!searchQuery.trim()) return collections;
    const query = searchQuery.toLowerCase();
    return collections.filter(collection => 
      collection.name.toLowerCase().includes(query)
    );
  }, [collections, searchQuery]);

  return (
    <div className="collection-manager">
      <div className="collection-header">
        <div className="collection-header-top">
          <h3>
            <Folder size={16} style={{ display: 'inline', verticalAlign: 'middle', marginRight: '8px' }} />
            Collections
          </h3>
          <button onClick={() => setShowCreateDialog(true)} className="create-btn">
            New
          </button>
        </div>
        <div className="collection-header-bottom">
          <div className="search-container">
            <Search size={16} className="search-icon" />
            <input
              type="text"
              className="search-input"
              placeholder="Search collections..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
            />
            {searchQuery && (
              <button
                className="search-clear-btn"
                onClick={() => setSearchQuery('')}
                aria-label="Clear search"
              >
                <XIcon size={14} />
              </button>
            )}
          </div>
          <button 
            onClick={loadCollections} 
            className="refresh-btn" 
            disabled={loading}
            title="Refresh collections"
          >
          </button>
        </div>
      </div>

      {error && (
        <div className="error-message">{error}</div>
      )}

      {showCreateDialog && (
        <div className="modal-overlay" onClick={handleCloseDialog}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <h3>
              <Sparkles size={20} style={{ display: 'inline', verticalAlign: 'middle', marginRight: '8px' }} />
              Create New Collection
            </h3>
            
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
                  placeholder="http://10.150.10.120:6000"
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
          <div>
            {Array.from({ length: 3 }).map((_, index) => (
              <div key={index} className="collection-item" style={{ pointerEvents: 'none' }}>
                <div className="collection-info">
                  <Skeleton width="70%" height={20} variant="text" />
                  <Skeleton width="40%" height={16} variant="text" />
                </div>
              </div>
            ))}
          </div>
        ) : filteredCollections.length === 0 ? (
          <div className="empty-state">
            <Inbox size={48} style={{ opacity: 0.3, marginBottom: '16px' }} />
            <p style={{ margin: 0, fontWeight: 'var(--font-medium, 500)' }}>
              {searchQuery ? 'No collections match your search' : 'No collections found'}
            </p>
            <p style={{ margin: '8px 0 0 0', fontSize: 'var(--text-sm, 14px)', color: 'var(--text-secondary, #666)' }}>
              {searchQuery ? 'Try a different search term' : 'Create a new collection to start organizing your documents'}
            </p>
            {!searchQuery && (
              <button
                onClick={() => setShowCreateDialog(true)}
                style={{
                  marginTop: '16px',
                  padding: 'var(--spacing-sm, 8px) var(--spacing-md, 16px)',
                  background: 'var(--primary, #3b82f6)',
                  color: 'white',
                  border: 'none',
                  borderRadius: 'var(--radius-md, 6px)',
                  cursor: 'pointer',
                  fontSize: 'var(--text-sm, 14px)',
                  fontWeight: 'var(--font-medium, 500)',
                }}
              >
                Create Collection
              </button>
            )}
          </div>
        ) : (
          filteredCollections.map((collection) => (
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
                  <BarChart3 size={14} style={{ display: 'inline', verticalAlign: 'middle', marginRight: '4px' }} />
                  {collection.chunk_count} chunks
                  {collection.embedding_dim && (
                    <span className="embedding-dim">• {collection.embedding_dim}D</span>
                  )}
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

      <ConfirmDialog
        isOpen={deleteConfirm.isOpen}
        title="Delete Collection"
        message={`Are you sure you want to delete collection "${deleteConfirm.name}"? This action cannot be undone.`}
        confirmText="Delete"
        cancelText="Cancel"
        variant="danger"
        onConfirm={confirmDelete}
        onCancel={() => setDeleteConfirm({ isOpen: false, name: '' })}
      />
    </div>
  );
};

