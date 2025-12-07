import { useState, FormEvent, useEffect, useRef } from 'react'
import { getPipelines } from '../api/config'
import './SearchForm.css'

interface SearchFormProps {
  onSearch: (query: string, pipelineName?: string) => void
  loading: boolean
}

function SearchForm({ onSearch, loading }: SearchFormProps) {
  const [query, setQuery] = useState('')
  const [pipelines, setPipelines] = useState<string[]>([])
  const [defaultPipeline, setDefaultPipeline] = useState<string>('')
  const [selectedPipeline, setSelectedPipeline] = useState<string>('')
  const inputRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    loadPipelines()
  }, [])

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && document.activeElement === inputRef.current) {
        setQuery('')
        inputRef.current?.blur()
      }
    }
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [])

  const loadPipelines = async () => {
    try {
      const data = await getPipelines()
      setPipelines(data.pipelines)
      setDefaultPipeline(data.default || '')
      setSelectedPipeline(data.default || '')
    } catch (err) {
      console.error('Failed to load pipelines:', err)
    }
  }

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault()
    if (!loading && query.trim()) {
      onSearch(query, selectedPipeline || undefined)
    }
  }

  return (
    <form className="search-form" onSubmit={handleSubmit}>
      <div className="search-input-container">
        {pipelines.length > 0 && (
          <div className="pipeline-selector-wrapper">
            <select
              className="pipeline-selector"
              value={selectedPipeline}
              onChange={(e) => setSelectedPipeline(e.target.value)}
              disabled={loading}
            >
              {pipelines.map((pipeline) => (
                <option key={pipeline} value={pipeline}>
                  {pipeline} {pipeline === defaultPipeline ? '(default)' : ''}
                </option>
              ))}
            </select>
          </div>
        )}
        <div className="search-input-wrapper">
          <span className="search-icon">🔍</span>
          <input
            ref={inputRef}
            type="text"
            className="search-input"
            placeholder="Enter your question..."
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            disabled={loading}
          />
          {query && !loading && (
            <button
              type="button"
              className="clear-button"
              onClick={() => setQuery('')}
              aria-label="Clear"
            >
              ✕
            </button>
          )}
        </div>
        <button
          type="submit"
          className="search-button"
          disabled={loading || !query.trim()}
        >
          {loading ? (
            <>
              <span className="loading-spinner"></span>
              <span>Searching...</span>
            </>
          ) : (
            'Search'
          )}
        </button>
      </div>
    </form>
  )
}

export default SearchForm

