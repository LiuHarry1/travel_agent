import { useState } from 'react'
import type { ParsedPipelineConfig } from '../api/config'
import './PipelineFlowchart.css'

interface PipelineFlowchartProps {
  config: ParsedPipelineConfig | null
}

function PipelineFlowchart({ config }: PipelineFlowchartProps) {
  const [isExpanded, setIsExpanded] = useState(true)

  if (!config) {
    return null
  }

  // Parse embedding models - ensure it's an array
  let embeddingModels: any[] = []
  if (config.embedding_models) {
    if (Array.isArray(config.embedding_models)) {
      embeddingModels = config.embedding_models
    } else if (typeof config.embedding_models === 'string') {
      // Handle case where it's a single string
      embeddingModels = [config.embedding_models]
    } else if (typeof config.embedding_models === 'object' && config.embedding_models !== null) {
      // Handle case where it's an object (shouldn't happen, but be safe)
      embeddingModels = [config.embedding_models]
    }
  }
  
  // Ensure embeddingModels is always an array
  if (!Array.isArray(embeddingModels)) {
    embeddingModels = []
  }
  
  const hasRerank = config.rerank?.api_url && typeof config.rerank.api_url === 'string' && config.rerank.api_url.trim() !== ''

  const steps = [
    {
      id: 'query',
      name: 'Query Input',
      type: 'input',
      enabled: true,
    },
    {
      id: 'embedding',
      name: 'Embedding Models',
      type: 'parallel',
      enabled: true,
      models: embeddingModels.map((model: any) => {
        let modelName = 'unknown'
        if (typeof model === 'string') {
          // Parse model string like "qwen" or "qwen:text-embedding-v2" or "qwen:collection"
          const parts = model.split(':')
          modelName = parts[0] || model
        } else if (typeof model === 'object' && model !== null) {
          modelName = model.model || model.name || 'unknown'
        }
        
        let collection = config.milvus?.collection || 'default'
        if (typeof model === 'string') {
          // Check if model string has collection: "qwen:collection" or "qwen:model:collection"
          const parts = model.split(':')
          if (parts.length === 2 && !parts[1].includes('/')) {
            // Could be model:collection format
            collection = parts[1]
          } else if (parts.length === 3) {
            collection = parts[2]
          }
        } else if (typeof model === 'object' && model !== null && model.collection) {
          collection = model.collection
        }
        
        return {
          name: modelName,
          collection: collection,
        }
      }),
      params: {
        top_k_per_model: config.retrieval?.top_k_per_model || 10,
        initial_search: config.chunk_sizes?.initial_search || 100,
      },
    },
    {
      id: 'merge',
      name: 'Merge Results',
      type: 'process',
      enabled: true,
    },
    {
      id: 'deduplicate',
      name: 'Deduplication',
      type: 'process',
      enabled: true,
    },
    {
      id: 'rerank',
      name: 'Rerank',
      type: 'process',
      enabled: hasRerank,
      params: hasRerank ? {
        api_url: config.rerank?.api_url || '',
        rerank_top_k: config.retrieval?.rerank_top_k || 20,
        rerank_input: config.chunk_sizes?.rerank_input || 50,
      } : undefined,
    },
    {
      id: 'llm_filter',
      name: 'LLM Filter',
      type: 'process',
      enabled: true,
      params: {
        model: config.llm_filter?.model || 'unknown',
        final_top_k: config.retrieval?.final_top_k || 10,
        llm_filter_input: config.chunk_sizes?.llm_filter_input || 20,
      },
    },
    {
      id: 'results',
      name: 'Final Results',
      type: 'output',
      enabled: true,
    },
  ]

  return (
    <div className="pipeline-flowchart">
      <button
        className="flowchart-header"
        onClick={() => setIsExpanded(!isExpanded)}
      >
        <h3 className="flowchart-title">Pipeline Flow</h3>
        <span className="expand-icon">{isExpanded ? '▼' : '▶'}</span>
      </button>

      {isExpanded && (
        <div className="flowchart-content">
          <div className="flowchart-steps">
            {steps.map((step, index) => (
              <div key={step.id} className="step-wrapper">
                {index > 0 && (
                  <div className={`step-connector ${step.enabled ? 'enabled' : 'disabled'}`}>
                    <div className="connector-line"></div>
                    <div className="connector-arrow">→</div>
                  </div>
                )}
                <div className={`step-node step-${step.type} ${step.enabled ? 'enabled' : 'disabled'}`}>
                  <div className="step-header">
                    <span className="step-name">{step.name}</span>
                    {!step.enabled && <span className="step-badge disabled-badge">Not Enabled</span>}
                  </div>
                  {step.type === 'parallel' && step.models && (
                    <div className="step-models">
                      {step.models.map((model, idx) => (
                        <div key={idx} className="model-item">
                          <span className="model-name">{model.name}</span>
                          <span className="model-collection">{model.collection}</span>
                        </div>
                      ))}
                    </div>
                  )}
                  {step.params && (
                    <div className="step-params">
                      {step.params.api_url && (
                        <div className="param-item">
                          <span className="param-label">API:</span>
                          <span className="param-value">{step.params.api_url}</span>
                        </div>
                      )}
                      {step.params.model && (
                        <div className="param-item">
                          <span className="param-label">Model:</span>
                          <span className="param-value">{step.params.model}</span>
                        </div>
                      )}
                      {step.params.top_k_per_model !== undefined && (
                        <div className="param-item">
                          <span className="param-label">Top K:</span>
                          <span className="param-value">{step.params.top_k_per_model}</span>
                        </div>
                      )}
                      {step.params.initial_search !== undefined && (
                        <div className="param-item">
                          <span className="param-label">Initial Search:</span>
                          <span className="param-value">{step.params.initial_search}</span>
                        </div>
                      )}
                      {step.params.rerank_top_k !== undefined && (
                        <div className="param-item">
                          <span className="param-label">Rerank Top K:</span>
                          <span className="param-value">{step.params.rerank_top_k}</span>
                        </div>
                      )}
                      {step.params.rerank_input !== undefined && (
                        <div className="param-item">
                          <span className="param-label">Rerank Input:</span>
                          <span className="param-value">{step.params.rerank_input}</span>
                        </div>
                      )}
                      {step.params.final_top_k !== undefined && (
                        <div className="param-item">
                          <span className="param-label">Final Top K:</span>
                          <span className="param-value">{step.params.final_top_k}</span>
                        </div>
                      )}
                      {step.params.llm_filter_input !== undefined && (
                        <div className="param-item">
                          <span className="param-label">LLM Input:</span>
                          <span className="param-value">{step.params.llm_filter_input}</span>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

export default PipelineFlowchart

