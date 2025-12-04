import React, { useState, useEffect } from 'react';
import { apiClient } from '../api/client';
import { Collection } from '../types/collection';
import './CollectionManager.css';

interface CollectionManagerProps {
  currentCollection: string;
  onCollectionChange: (name: string) => void;
  refreshTrigger?: number; // When this changes, refresh collections
}

export const CollectionManager: React.FC<CollectionManagerProps> = ({
  currentCollection,
  onCollectionChange,
  refreshTrigger,
}) => {
  const [collections, setCollections] = useState<Collection[]>([]);
  const [loading, setLoading] = useState(false);
  const [showCreateDialog, setShowCreateDialog] = useState(false);
  const [newCollectionName, setNewCollectionName] = useState('');
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState<string | null>(null);

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

  const handleCreate = async () => {
    if (!newCollectionName.trim()) return;
    
    setCreating(true);
    setError(null);
    try {
      await apiClient.createCollection(newCollectionName.trim());
      setShowCreateDialog(false);
      setNewCollectionName('');
      await loadCollections();
      onCollectionChange(newCollectionName.trim());
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create collection');
      console.error('Failed to create collection:', err);
    } finally {
      setCreating(false);
    }
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
        <div className="modal-overlay" onClick={() => setShowCreateDialog(false)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <h3>Create New Collection</h3>
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
            <div className="modal-actions">
              <button onClick={handleCreate} disabled={creating || !newCollectionName.trim()}>
                {creating ? 'Creating...' : 'Create'}
              </button>
              <button onClick={() => setShowCreateDialog(false)} disabled={creating}>
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

