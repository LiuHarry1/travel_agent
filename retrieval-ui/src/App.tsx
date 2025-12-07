import { useState } from 'react'
import './App.css'
import SearchForm from './components/SearchForm'
import ResultsDisplay from './components/ResultsDisplay'
import ConfigManager from './components/ConfigManager'
import { searchWithDebug } from './api/retrieval'
import type { DebugRetrievalResponse } from './types'

type Tab = 'search' | 'config'

function App() {
  const [activeTab, setActiveTab] = useState<Tab>('search')
  const [loading, setLoading] = useState(false)
  const [results, setResults] = useState<DebugRetrievalResponse | null>(null)
  const [error, setError] = useState<string | null>(null)

  const handleSearch = async (query: string, pipelineName?: string) => {
    if (!query.trim()) {
      setError('Please enter a query')
      return
    }

    setLoading(true)
    setError(null)
    setResults(null)

    try {
      const data = await searchWithDebug(query, pipelineName)
      setResults(data)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="app">
      <aside className="app-sidebar">
        <div className="sidebar-header">
          <h1 className="sidebar-logo">Retrieval</h1>
          <p className="sidebar-subtitle">RAG System</p>
        </div>
        <nav className="sidebar-nav">
          <button
            className={`nav-item ${activeTab === 'search' ? 'active' : ''}`}
            onClick={() => setActiveTab('search')}
          >
            <span className="nav-icon">🔍</span>
            <span className="nav-label">Search</span>
          </button>
          <button
            className={`nav-item ${activeTab === 'config' ? 'active' : ''}`}
            onClick={() => setActiveTab('config')}
          >
            <span className="nav-icon">⚙️</span>
            <span className="nav-label">Configuration</span>
          </button>
        </nav>
      </aside>

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
  )
}

export default App

