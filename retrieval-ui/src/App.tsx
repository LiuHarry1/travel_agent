import { useState } from 'react'
import './App.css'
import SearchForm from './components/SearchForm'
import ResultsDisplay from './components/ResultsDisplay'
import { searchWithDebug } from './api/retrieval'
import type { DebugRetrievalResponse } from './types'

function App() {
  const [loading, setLoading] = useState(false)
  const [results, setResults] = useState<DebugRetrievalResponse | null>(null)
  const [error, setError] = useState<string | null>(null)

  const handleSearch = async (query: string) => {
    if (!query.trim()) {
      setError('请输入查询内容')
      return
    }

    setLoading(true)
    setError(null)
    setResults(null)

    try {
      const data = await searchWithDebug(query)
      setResults(data)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="app">
      <header className="app-header">
        <h1>检索系统</h1>
        <p>多模型检索、重排序与LLM过滤</p>
      </header>

      <main className="app-main">
        <SearchForm onSearch={handleSearch} loading={loading} />

        {error && (
          <div className="error-message">
            <strong>错误:</strong> {error}
          </div>
        )}

        {results && <ResultsDisplay results={results} />}
      </main>
    </div>
  )
}

export default App

