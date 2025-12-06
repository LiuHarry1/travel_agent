import { useState, FormEvent } from 'react'
import './SearchForm.css'

interface SearchFormProps {
  onSearch: (query: string) => void
  loading: boolean
}

function SearchForm({ onSearch, loading }: SearchFormProps) {
  const [query, setQuery] = useState('')

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault()
    if (!loading && query.trim()) {
      onSearch(query)
    }
  }

  return (
    <form className="search-form" onSubmit={handleSubmit}>
      <div className="search-input-container">
        <input
          type="text"
          className="search-input"
          placeholder="请输入您的问题..."
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          disabled={loading}
        />
        <button
          type="submit"
          className="search-button"
          disabled={loading || !query.trim()}
        >
          {loading ? '搜索中...' : '搜索'}
        </button>
      </div>
    </form>
  )
}

export default SearchForm

