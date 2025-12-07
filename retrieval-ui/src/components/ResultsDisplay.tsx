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
                <ChunkCard key={chunk.chunk_id || index} chunk={chunk} />
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
                    <ChunkCard key={chunk.chunk_id || index} chunk={chunk} />
                  ))
                )}
              </div>
            </div>
          ))}
        </div>
      )
    }
  }

  return (
    <div className="results-display">
      <div className="query-display">
        <h2>Query: "{results.query}"</h2>
        <p className="summary">
          Found {results.results.length} final result{results.results.length !== 1 ? 's' : ''}
        </p>
      </div>

      <div className="sections">
        {sections.map((section) => {
          const isExpanded = expandedSection === section.key
          const data = section.data
          const count = Array.isArray(data) ? data.length : Object.values(data).flat().length

          return (
            <div key={section.key} className="section">
              <button
                className="section-header"
                onClick={() => toggleSection(section.key)}
              >
                <span className="section-title">
                  {section.title}
                  <span className="count-badge">{count}</span>
                </span>
                <span className="expand-icon">{isExpanded ? '▼' : '▶'}</span>
              </button>

              {isExpanded && (
                <div className="section-content">
                  {renderChunks(data)}
                </div>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}

interface ChunkCardProps {
  chunk: DebugChunkResult
}

function ChunkCard({ chunk }: ChunkCardProps) {
  return (
    <div className="chunk-card">
      <div className="chunk-header">
        <span className="chunk-id">ID: {chunk.chunk_id}</span>
        {chunk.embedder && (
          <span className="chunk-embedder">{chunk.embedder}</span>
        )}
        {chunk.score !== undefined && (
          <span className="chunk-score">Score: {chunk.score.toFixed(4)}</span>
        )}
        {chunk.rerank_score !== undefined && (
          <span className="chunk-rerank-score">
            Rerank Score: {chunk.rerank_score.toFixed(4)}
          </span>
        )}
      </div>
      <div className="chunk-text">{chunk.text}</div>
    </div>
  )
}

export default ResultsDisplay

