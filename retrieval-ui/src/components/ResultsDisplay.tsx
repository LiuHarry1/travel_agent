import { useState } from 'react'
import type { DebugRetrievalResponse, DebugChunkResult } from '../types'
import './ResultsDisplay.css'

interface ResultsDisplayProps {
  results: DebugRetrievalResponse
}

function ResultsDisplay({ results }: ResultsDisplayProps) {
  const [expandedSection, setExpandedSection] = useState<string | null>('final')

  const sections = [
    { key: 'model_results', title: 'Model Search Results', data: results.debug.model_results },
    { key: 'deduplicated', title: 'Deduplicated Results', data: results.debug.deduplicated },
    { key: 'reranked', title: 'Re-ranked Results', data: results.debug.reranked },
    { key: 'final', title: 'Final Results (LLM Filtered)', data: results.debug.final },
  ]

  const toggleSection = (key: string) => {
    setExpandedSection(expandedSection === key ? null : key)
  }

  const renderChunks = (chunks: DebugChunkResult[] | Record<string, DebugChunkResult[]>) => {
    if (Array.isArray(chunks)) {
      return (
        <div className="chunks-list">
          {chunks.length === 0 ? (
            <p className="empty-message">No results found</p>
          ) : (
              chunks.map((chunk, index) => (
                <ChunkCard 
                  key={`chunk-${chunk.chunk_id}-${index}-${chunk.embedder || ''}`} 
                  chunk={chunk}
                  defaultExpanded={false}
                />
              ))
          )}
        </div>
      )
    } else {
      // Model results - grouped by embedder
      return (
        <div className="model-results">
          {Object.entries(chunks).map(([embedder, chunksList]) => (
            <div key={embedder} className="model-group">
              <h4 className="model-name">{embedder}</h4>
              <div className="chunks-list">
                {chunksList.length === 0 ? (
                  <p className="empty-message">No results found</p>
                ) : (
                  chunksList.map((chunk, index) => (
                    <ChunkCard 
                      key={`chunk-${embedder}-${chunk.chunk_id}-${index}`} 
                      chunk={chunk}
                      defaultExpanded={false}
                    />
                  ))
                )}
              </div>
            </div>
          ))}
        </div>
      )
    }
  }

  const timing = results.debug?.timing
  const formatTime = (ms?: number) => {
    if (ms === undefined) return 'N/A'
    if (ms < 1) return `${(ms * 1000).toFixed(2)}μs`
    if (ms < 1000) return `${ms.toFixed(2)}ms`
    return `${(ms / 1000).toFixed(2)}s`
  }

  return (
    <div className="results-display">
      <div className="query-display">
        <div className="query-header">
          <h2 className="query-text">"{results.query}"</h2>
          <div className="query-meta">
            <span className="result-count">
              {results.results.length} result{results.results.length !== 1 ? 's' : ''}
            </span>
            {timing?.total && (
              <span className="total-time">
                Total: {formatTime(timing.total)}
              </span>
            )}
          </div>
        </div>
      </div>

      <div className="sections">
        {sections.map((section, index) => {
          const isExpanded = expandedSection === section.key
          const data = section.data
          const count = Array.isArray(data) ? data.length : Object.values(data).flat().length
          
          // Get timing for this section
          let sectionTime: number | undefined
          if (timing) {
            if (section.key === 'model_results') {
              sectionTime = timing.embedding_total
            } else if (section.key === 'deduplicated') {
              sectionTime = timing.deduplication
            } else if (section.key === 'reranked') {
              sectionTime = timing.rerank
            } else if (section.key === 'final') {
              sectionTime = timing.llm_filter
            }
          }

          return (
            <div key={section.key} className="section-wrapper">
              {index > 0 && <div className="section-connector"></div>}
              <div className="section">
                <button
                  className={`section-header ${isExpanded ? 'expanded' : ''}`}
                  onClick={() => toggleSection(section.key)}
                >
                  <span className="section-title">
                    <span className="section-name">{section.title}</span>
                    <span className="count-badge">{count}</span>
                    {sectionTime !== undefined && (
                      <span className="time-badge">{formatTime(sectionTime)}</span>
                    )}
                  </span>
                  <span className="expand-icon">{isExpanded ? '▼' : '▶'}</span>
                </button>

                {isExpanded && (
                  <div className="section-content">
                    {renderChunks(data)}
                  </div>
                )}
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}

interface ChunkCardProps {
  chunk: DebugChunkResult
  defaultExpanded?: boolean
}

function ChunkCard({ chunk, defaultExpanded = false }: ChunkCardProps) {
  const [isExpanded, setIsExpanded] = useState(defaultExpanded)

  const handleToggle = (e: React.MouseEvent) => {
    e.preventDefault()
    e.stopPropagation()
    setIsExpanded(prev => !prev)
  }

  const hasText = chunk.text && chunk.text.trim().length > 0
  const textPreview = hasText ? chunk.text.substring(0, 150) + (chunk.text.length > 150 ? '...' : '') : ''

  // Score color coding: lower is better for distance scores
  const getScoreColor = (score: number) => {
    if (score < 0.5) return '#10B981' // green - very good
    if (score < 1.0) return '#3B82F6' // blue - good
    if (score < 2.0) return '#F59E0B' // orange - moderate
    return '#EF4444' // red - poor
  }

  return (
    <div className={`chunk-card ${isExpanded ? 'expanded' : ''}`}>
      <div className="chunk-header" onClick={handleToggle}>
        <div className="chunk-meta">
          <span className="chunk-id">ID: {chunk.chunk_id}</span>
          {chunk.embedder && (
            <span className="chunk-embedder">{chunk.embedder}</span>
          )}
        </div>
        <div className="chunk-scores">
          {chunk.score !== undefined && (
            <span 
              className="chunk-score" 
              style={{ color: getScoreColor(chunk.score) }}
              title="Similarity score (lower is better)"
            >
              Score: {chunk.score.toFixed(4)}
            </span>
          )}
          {chunk.rerank_score !== undefined && (
            <span 
              className="chunk-rerank-score"
              title="Re-ranking score"
            >
              Rerank: {chunk.rerank_score.toFixed(4)}
            </span>
          )}
        </div>
        <span 
          className="expand-toggle" 
          onClick={handleToggle}
          title={isExpanded ? 'Click to collapse' : 'Click to expand'}
        >
          {isExpanded ? '▼' : '▶'}
        </span>
      </div>
      {isExpanded ? (
        <div className="chunk-text" onClick={handleToggle}>
          {hasText ? (
            chunk.text
          ) : (
            <em className="empty-text">No text content available</em>
          )}
        </div>
      ) : (
        hasText && (
          <div className="chunk-preview" onClick={handleToggle}>
            {textPreview}
          </div>
        )
      )}
    </div>
  )
}

export default ResultsDisplay

