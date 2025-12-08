import { useState, useCallback } from 'react'
import './App.css'
import SearchForm from './components/SearchForm'
import ResultsDisplay from './components/ResultsDisplay'
import ConfigManager from './components/ConfigManager'
import { searchWithDebug } from './api/retrieval'
import { handleApiError } from './utils/errorHandler'
import { UI_TEXT } from './constants'
import type { DebugRetrievalResponse } from './types'

type Tab = 'search' | 'config'

function App() {
  const [activeTab, setActiveTab] = useState<Tab>('search')
  const [loading, setLoading] = useState(false)
  const [results, setResults] = useState<DebugRetrievalResponse | null>(null)
  const [error, setError] = useState<string | null>(null)

  const handleSearch = useCallback(async (query: string, pipelineName?: string) => {
    if (!query.trim()) {
      setError(UI_TEXT.ERRORS.EMPTY_QUERY)
      return
    }

    setLoading(true)
    setError(null)
    setResults(null)

    try {
      const data = await searchWithDebug(query, pipelineName)
      setResults(data)
    } catch (err) {
      const errorMessage = handleApiError('Search failed', err)
      setError(errorMessage)
    } finally {
      setLoading(false)
    }
  }, [])

  return (
    <div className="app">
      <aside className="app-sidebar">
        <div className="sidebar-header">
          <div className="sidebar-logo-container">
            <div className="sidebar-logo-icon">🔍</div>
            <div>
              <h1 className="sidebar-logo">Retrieval</h1>
              <p className="sidebar-subtitle">RAG System</p>
            </div>
          </div>
        </div>
        <nav className="sidebar-nav">
          <button
            className={`nav-item ${activeTab === 'search' ? 'active' : ''}`}
            onClick={() => setActiveTab('search')}
            aria-label="Search"
          >
            <span className="nav-icon">🔍</span>
            <span className="nav-label">Search</span>
            {activeTab === 'search' && <span className="nav-indicator"></span>}
          </button>
          <button
            className={`nav-item ${activeTab === 'config' ? 'active' : ''}`}
            onClick={() => setActiveTab('config')}
            aria-label="Configuration"
          >
            <span className="nav-icon">⚙️</span>
            <span className="nav-label">Configuration</span>
            {activeTab === 'config' && <span className="nav-indicator"></span>}
          </button>
        </nav>
        <div className="sidebar-footer">
          <p className="sidebar-footer-text">Retrieval UI v1.0</p>
        </div>
      </aside>

      <div className="app-content-wrapper">
        <main className="app-main">
          {activeTab === 'search' && (
            <>
              <SearchForm onSearch={handleSearch} loading={loading} />

              {error && (
                <div className="error-message">
                  <strong>Error:</strong> {error}
                </div>
              )}

              {results && <ResultsDisplay results={results} />}
            </>
          )}

          {activeTab === 'config' && <ConfigManager />}
        </main>
      </div>
    </div>
  )
}

export default App

