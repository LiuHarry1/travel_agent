import { useState, memo } from 'react'
import type { DebugChunkResult } from '../types'
import { SCORE_THRESHOLDS, SCORE_COLORS, TEXT_PREVIEW_LENGTH } from '../constants'
import './ChunkCard.css'

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
  const textPreview = hasText
    ? chunk.text.substring(0, TEXT_PREVIEW_LENGTH) + (chunk.text.length > TEXT_PREVIEW_LENGTH ? '...' : '')
    : ''

  // Score color coding: lower is better for distance scores
  const getScoreColor = (score: number) => {
    if (score < SCORE_THRESHOLDS.EXCELLENT) return SCORE_COLORS.EXCELLENT
    if (score < SCORE_THRESHOLDS.GOOD) return SCORE_COLORS.GOOD
    if (score < SCORE_THRESHOLDS.MODERATE) return SCORE_COLORS.MODERATE
    return SCORE_COLORS.POOR
  }

  return (
    <div className={`chunk-card ${isExpanded ? 'expanded' : ''}`}>
      <div className="chunk-header" onClick={handleToggle}>
        <div className="chunk-meta">
          <span className="chunk-id">ID: {chunk.chunk_id}</span>
          {chunk.embedder && <span className="chunk-embedder">{chunk.embedder}</span>}
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
            <span className="chunk-rerank-score" title="Re-ranking score">
              Rerank: {chunk.rerank_score.toFixed(4)}
            </span>
          )}
        </div>
        <span
          className="expand-toggle"
          onClick={handleToggle}
          title={isExpanded ? 'Click to collapse' : 'Click to expand'}
          aria-label={isExpanded ? 'Collapse' : 'Expand'}
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

export default memo(ChunkCard)

