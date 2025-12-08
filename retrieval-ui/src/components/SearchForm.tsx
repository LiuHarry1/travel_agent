import { useState, FormEvent, useEffect, useRef, useCallback, memo } from 'react'
import { usePipelines } from '../hooks/usePipelines'
import { UI_TEXT } from '../constants'
import './SearchForm.css'

interface SearchFormProps {
  onSearch: (query: string, pipelineName?: string) => void
  loading: boolean
}

function SearchForm({ onSearch, loading }: SearchFormProps) {
  const [query, setQuery] = useState('')
  const [selectedPipeline, setSelectedPipeline] = useState<string>('')
  const inputRef = useRef<HTMLInputElement>(null)
  const { pipelines } = usePipelines()

  useEffect(() => {
    if (pipelines.pipelines.length > 0 && !selectedPipeline) {
      setSelectedPipeline(pipelines.default || pipelines.pipelines[0])
    }
  }, [pipelines, selectedPipeline])

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

  const handleSubmit = useCallback(
    (e: FormEvent) => {
      e.preventDefault()
      if (!loading && query.trim()) {
        onSearch(query, selectedPipeline || undefined)
      }
    },
    [loading, query, selectedPipeline, onSearch]
  )

  const handleClear = useCallback(() => {
    setQuery('')
    inputRef.current?.focus()
  }, [])

  return (
    <form className="search-form" onSubmit={handleSubmit}>
      <div className="search-input-container">
        {pipelines.pipelines.length > 0 && (
          <div className="pipeline-selector-wrapper">
            <select
              className="pipeline-selector"
              value={selectedPipeline}
              onChange={(e) => setSelectedPipeline(e.target.value)}
              disabled={loading}
              aria-label="Select pipeline"
            >
              {pipelines.pipelines.map((pipeline) => (
                <option key={pipeline} value={pipeline}>
                  {pipeline} {pipeline === pipelines.default ? UI_TEXT.PIPELINE.DEFAULT : ''}
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
            placeholder={UI_TEXT.SEARCH.PLACEHOLDER}
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            disabled={loading}
          />
          {query && !loading && (
            <button
              type="button"
              className="clear-button"
              onClick={handleClear}
              aria-label={UI_TEXT.SEARCH.CLEAR}
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
              <span>{UI_TEXT.SEARCH.BUTTON_LOADING}</span>
            </>
          ) : (
            UI_TEXT.SEARCH.BUTTON
          )}
        </button>
      </div>
    </form>
  )
}

export default memo(SearchForm)

