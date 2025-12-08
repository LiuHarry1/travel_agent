import { useState, useMemo, memo } from 'react'
import type { DebugRetrievalResponse, DebugChunkResult } from '../types'
import ChunkCard from './ChunkCard'
import { TIME_FORMAT } from '../constants'
import './ResultsDisplay.css'

interface ResultsDisplayProps {
  results: DebugRetrievalResponse
}

function ResultsDisplay({ results }: ResultsDisplayProps) {
  const [expandedSection, setExpandedSection] = useState<string | null>('final')

  const sections = useMemo(
    () => {
      const sectionsList = [
        { key: 'model_results', title: 'Model Search Results', data: results.debug.model_results },
        { key: 'deduplicated', title: 'Deduplicated Results', data: results.debug.deduplicated },
      ]
      
      // Only include reranked section if it exists in debug results
      if (results.debug.reranked !== undefined) {
        sectionsList.push({ key: 'reranked', title: 'Re-ranked Results', data: results.debug.reranked })
      }
      
      // Determine final section title based on whether LLM filter was used
      const hasLLMFiltering = results.debug.timing?.llm_filtering !== undefined || 
                              results.debug.timing?.llm_filter !== undefined
      const finalTitle = hasLLMFiltering 
        ? 'Final Results (LLM Filtered)' 
        : 'Final Results'
      
      // Always include final section
      sectionsList.push({ key: 'final', title: finalTitle, data: results.debug.final })
      
      return sectionsList
    },
    [results.debug]
  )

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
  
  const formatTime = (ms?: number): string => {
    if (ms === undefined) return 'N/A'
    if (ms < 1) return `${(ms * 1000).toFixed(2)}${TIME_FORMAT.MICROSECONDS}`
    if (ms < 1000) return `${ms.toFixed(2)}${TIME_FORMAT.MILLISECONDS}`
    return `${(ms / 1000).toFixed(2)}${TIME_FORMAT.SECONDS}`
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
              // Backend returns 'reranking' not 'rerank'
              sectionTime = timing.reranking ?? timing.rerank
            } else if (section.key === 'final') {
              // Backend returns 'llm_filtering' not 'llm_filter'
              sectionTime = timing.llm_filtering ?? timing.llm_filter
            }
          }

          // Show time badge if timing exists (including 0, but not undefined or null)
          const showTime = sectionTime !== undefined && sectionTime !== null

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
                    {showTime && (
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

export default memo(ResultsDisplay)

