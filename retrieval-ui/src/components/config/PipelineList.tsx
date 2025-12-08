import { memo } from 'react'
import type { PipelineList } from '../../api/config'
import './PipelineList.css'

interface PipelineListProps {
  pipelines: PipelineList
  selectedPipeline: string
  onSelect: (pipelineName: string) => void
  onSetDefault: (pipelineName: string) => void
  onCreate: () => void
  loading?: boolean
}

function PipelineListComponent({
  pipelines,
  selectedPipeline,
  onSelect,
  onSetDefault,
  onCreate,
  loading = false,
}: PipelineListProps) {
  return (
    <div className="config-sidebar">
      <div className="sidebar-header-section">
        <h3>Pipelines</h3>
        <button
          className="btn btn-primary btn-small"
          onClick={onCreate}
          disabled={loading}
          aria-label="Create new pipeline"
        >
          + New
        </button>
      </div>
      {loading && !pipelines.pipelines.length ? (
        <div className="loading">Loading pipelines...</div>
      ) : (
        <ul className="pipeline-list">
          {pipelines.pipelines.map((pipeline) => (
            <li key={pipeline}>
              <div
                className={`pipeline-item ${selectedPipeline === pipeline ? 'active' : ''}`}
                onClick={() => onSelect(pipeline)}
                role="button"
                tabIndex={0}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault()
                    onSelect(pipeline)
                  }
                }}
                aria-label={`Select pipeline ${pipeline}`}
              >
                <span className="pipeline-name">{pipeline}</span>
                {pipeline === pipelines.default && (
                  <span className="default-badge">default</span>
                )}
                {pipeline === pipelines.default ? (
                  <span
                    className="set-default-btn disabled"
                    title="Already default"
                    aria-label="Already default"
                  >
                    ★
                  </span>
                ) : (
                  <span
                    className="set-default-btn"
                    onClick={(e) => {
                      e.stopPropagation()
                      onSetDefault(pipeline)
                    }}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter' || e.key === ' ') {
                        e.preventDefault()
                        e.stopPropagation()
                        onSetDefault(pipeline)
                      }
                    }}
                    title="Set as default"
                    aria-label={`Set ${pipeline} as default`}
                    role="button"
                    tabIndex={0}
                  >
                    ☆
                  </span>
                )}
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}

export default memo(PipelineListComponent)

