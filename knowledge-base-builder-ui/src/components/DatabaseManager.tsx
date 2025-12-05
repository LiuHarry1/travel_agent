import React, { useState, useEffect } from 'react';
import { apiClient } from '../api/client';
import './DatabaseManager.css';

interface DatabaseManagerProps {
  currentDatabase: string;
  onDatabaseChange: (database: string) => void;
}

export const DatabaseManager: React.FC<DatabaseManagerProps> = ({
  currentDatabase,
  onDatabaseChange,
}) => {
  const [databases, setDatabases] = useState<string[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [newDatabaseName, setNewDatabaseName] = useState('');
  const [creating, setCreating] = useState(false);

  useEffect(() => {
    loadDatabases();
  }, []);

  const loadDatabases = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await apiClient.listDatabases();
      setDatabases(data.databases);
      if (data.current && data.current !== currentDatabase) {
        onDatabaseChange(data.current);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load databases');
    } finally {
      setLoading(false);
    }
  };

  const handleCreateDatabase = async () => {
    if (!newDatabaseName.trim()) {
      setError('Database name cannot be empty');
      return;
    }

    // Validate database name (alphanumeric and underscores only)
    if (!/^[a-zA-Z0-9_]+$/.test(newDatabaseName)) {
      setError('Database name can only contain letters, numbers, and underscores');
      return;
    }

    setCreating(true);
    setError(null);
    try {
      await apiClient.createDatabase(newDatabaseName.trim());
      setNewDatabaseName('');
      setShowCreateModal(false);
      await loadDatabases();
      // Switch to the new database
      onDatabaseChange(newDatabaseName.trim());
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create database');
    } finally {
      setCreating(false);
    }
  };

  const handleDeleteDatabase = async (name: string) => {
    if (name === 'default') {
      setError('Cannot delete the default database');
      return;
    }

    if (!confirm(`Are you sure you want to delete database "${name}"? This action cannot be undone.`)) {
      return;
    }

    setLoading(true);
    setError(null);
    try {
      await apiClient.deleteDatabase(name);
      await loadDatabases();
      // If deleted database was current, switch to default
      if (name === currentDatabase) {
        onDatabaseChange('default');
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to delete database');
    } finally {
      setLoading(false);
    }
  };

  const handleSwitchDatabase = (name: string) => {
    if (name !== currentDatabase) {
      onDatabaseChange(name);
    }
  };

  return (
    <div className="database-manager">
      <div className="database-manager-header">
        <h3>Databases</h3>
        <button
          className="btn-create-db"
          onClick={() => setShowCreateModal(true)}
          title="Create new database"
        >
          + New
        </button>
      </div>

      {error && (
        <div className="database-error">{error}</div>
      )}

      {loading && databases.length === 0 ? (
        <div className="database-loading">Loading databases...</div>
      ) : (
        <div className="database-list">
          {databases.map((db) => (
            <div
              key={db}
              className={`database-item ${db === currentDatabase ? 'active' : ''}`}
              onClick={() => handleSwitchDatabase(db)}
            >
              <span className="database-name">{db}</span>
              {db === currentDatabase && (
                <span className="database-badge">Current</span>
              )}
              {db !== 'default' && (
                <button
                  className="btn-delete-db"
                  onClick={(e) => {
                    e.stopPropagation();
                    handleDeleteDatabase(db);
                  }}
                  title="Delete database"
                >
                  ×
                </button>
              )}
            </div>
          ))}
        </div>
      )}

      {showCreateModal && (
        <div className="modal-overlay" onClick={() => setShowCreateModal(false)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <h3>Create New Database</h3>
            <div className="form-group">
              <label htmlFor="db-name">Database Name</label>
              <input
                id="db-name"
                type="text"
                value={newDatabaseName}
                onChange={(e) => setNewDatabaseName(e.target.value)}
                placeholder="Enter database name"
                onKeyPress={(e) => {
                  if (e.key === 'Enter') {
                    handleCreateDatabase();
                  }
                }}
                autoFocus
              />
              <small>Only letters, numbers, and underscores are allowed</small>
            </div>
            <div className="modal-actions">
              <button
                className="btn-cancel"
                onClick={() => {
                  setShowCreateModal(false);
                  setNewDatabaseName('');
                  setError(null);
                }}
              >
                Cancel
              </button>
              <button
                className="btn-primary"
                onClick={handleCreateDatabase}
                disabled={creating || !newDatabaseName.trim()}
              >
                {creating ? 'Creating...' : 'Create'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

