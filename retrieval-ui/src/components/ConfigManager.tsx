import { useState, useEffect } from 'react'
import {
  getPipelines,
  getPipeline,
  createPipeline,
  updatePipeline,
  deletePipeline,
  validatePipeline,
  setDefaultPipeline,
  type PipelineList,
  type PipelineConfig,
  type ValidationResult,
} from '../api/config'
import PipelineFlowchart from './PipelineFlowchart'
import './ConfigManager.css'

function ConfigManager() {
  const [pipelines, setPipelines] = useState<PipelineList>({ default: null, pipelines: [] })
  const [selectedPipeline, setSelectedPipeline] = useState<string>('')
  const [yamlContent, setYamlContent] = useState<string>('')
  const [parsedConfig, setParsedConfig] = useState<any>(null)
  const [loading, setLoading] = useState(false)
  const [saving, setSaving] = useState(false)
  const [validating, setValidating] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState<string | null>(null)
  const [validationResult, setValidationResult] = useState<ValidationResult | null>(null)

  useEffect(() => {
    loadPipelines()
  }, [])

  useEffect(() => {
    if (selectedPipeline) {
      loadPipeline(selectedPipeline)
    } else {
      setYamlContent('')
      setValidationResult(null)
    }
  }, [selectedPipeline])

  const loadPipelines = async () => {
    try {
      setLoading(true)
      setError(null)
      const data = await getPipelines()
      console.log('Loaded pipelines:', data)
      setPipelines(data)
      if (data.pipelines.length > 0 && !selectedPipeline) {
        setSelectedPipeline(data.default || data.pipelines[0])
      }
    } catch (err) {
      console.error('Error loading pipelines:', err)
      setError(err instanceof Error ? err.message : 'Failed to load pipelines')
    } finally {
      setLoading(false)
    }
  }

  const parseYaml = (yaml: string) => {
    try {
      // Simple YAML parser for basic structure
      // For production, consider using a proper YAML parser library
      const lines = yaml.split('\n')
      const config: any = {}
      let currentSection: string | null = null
      let indentLevel = 0
      
      for (let i = 0; i < lines.length; i++) {
        const line = lines[i]
        const trimmed = line.trim()
        if (!trimmed || trimmed.startsWith('#')) continue
        
        // Calculate indentation
        const currentIndent = line.length - line.trimStart().length
        
        // Section header (e.g., "milvus:" or "embedding_models:")
        if (trimmed.endsWith(':') && !trimmed.startsWith('-')) {
          const sectionName = trimmed.slice(0, -1).trim()
          currentSection = sectionName
          indentLevel = currentIndent
          
          // Check if next line is an array item
          if (i + 1 < lines.length) {
            const nextLine = lines[i + 1]
            const nextTrimmed = nextLine.trim()
            const nextIndent = nextLine.length - nextLine.trimStart().length
            
            if (nextTrimmed.startsWith('-') && nextIndent > indentLevel) {
              // This section is an array
              config[currentSection] = []
            } else {
              // This section is an object
              config[currentSection] = {}
            }
          } else {
            config[currentSection] = {}
          }
        }
        // Array item (e.g., "  - qwen")
        else if (trimmed.startsWith('-') && currentSection) {
          const itemValue = trimmed.slice(1).trim()
          if (itemValue) {
            if (!Array.isArray(config[currentSection])) {
              config[currentSection] = []
            }
            config[currentSection].push(itemValue)
          }
        }
        // Key-value pair (e.g., "  host: localhost")
        else if (trimmed.includes(':') && currentSection && !trimmed.startsWith('-')) {
          const [key, ...valueParts] = trimmed.split(':')
          const keyTrimmed = key.trim()
          let value = valueParts.join(':').trim()
          
          // Remove quotes if present
          if ((value.startsWith("'") && value.endsWith("'")) || 
              (value.startsWith('"') && value.endsWith('"'))) {
            value = value.slice(1, -1)
          }
          
          if (typeof config[currentSection] === 'object' && !Array.isArray(config[currentSection])) {
            config[currentSection][keyTrimmed] = value
          }
        }
      }
      
      return config
    } catch (err) {
      console.error('Failed to parse YAML:', err)
      return null
    }
  }

  const loadPipeline = async (pipelineName: string) => {
    try {
      setLoading(true)
      setError(null)
      const data = await getPipeline(pipelineName)
      setYamlContent(data.yaml)
      setParsedConfig(parseYaml(data.yaml))
      setValidationResult(null)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load pipeline')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    if (yamlContent) {
      setParsedConfig(parseYaml(yamlContent))
    }
  }, [yamlContent])

  const handleSave = async () => {
    if (!selectedPipeline || !yamlContent.trim()) {
      setError('Please select a pipeline and provide configuration')
      return
    }

    try {
      setSaving(true)
      setError(null)
      setSuccess(null)

      // Validate before saving
      const validation = await validatePipeline(selectedPipeline, yamlContent)
      setValidationResult(validation)

      if (!validation.valid) {
        setError('Configuration validation failed. Please fix the errors before saving.')
        return
      }

      // Save configuration
      await updatePipeline(selectedPipeline, yamlContent)
      setSuccess('Configuration saved successfully!')
      
      // Reload pipelines to refresh list
      await loadPipelines()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save configuration')
    } finally {
      setSaving(false)
    }
  }

  const handleCreate = async () => {
    const pipelineName = prompt('Enter pipeline name:')
    if (!pipelineName) return

    if (pipelines.pipelines.includes(pipelineName)) {
      setError(`Pipeline '${pipelineName}' already exists`)
      return
    }

    try {
      setSaving(true)
      setError(null)
      setSuccess(null)

      // Use a template configuration
      const templateYaml = `milvus:
  host: localhost
  port: 19530
  user: ""
  password: ""
  database: default
  collection: memory_doc_db

embedding_models:
  - qwen

rerank:
  api_url: ""
  model: ""
  timeout: 30

llm_filter:
  api_key: env:DASHSCOPE_API_KEY
  base_url: https://dashscope.aliyuncs.com/compatible-mode/v1
  model: qwen-plus

retrieval:
  top_k_per_model: 10
  rerank_top_k: 20
  final_top_k: 10

chunk_sizes:
  initial_search: 100
  rerank_input: 50
  llm_filter_input: 20
`

      await createPipeline(pipelineName, templateYaml)
      setSuccess(`Pipeline '${pipelineName}' created successfully!`)
      
      // Reload and select new pipeline
      await loadPipelines()
      setSelectedPipeline(pipelineName)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create pipeline')
    } finally {
      setSaving(false)
    }
  }

  const handleDelete = async () => {
    if (!selectedPipeline) return

    if (!confirm(`Are you sure you want to delete pipeline '${selectedPipeline}'?`)) {
      return
    }

    try {
      setSaving(true)
      setError(null)
      await deletePipeline(selectedPipeline)
      setSuccess(`Pipeline '${selectedPipeline}' deleted successfully!`)
      
      // Reload pipelines and clear selection
      await loadPipelines()
      setSelectedPipeline('')
      setYamlContent('')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to delete pipeline')
    } finally {
      setSaving(false)
    }
  }

  const handleValidate = async () => {
    if (!selectedPipeline || !yamlContent.trim()) {
      setError('Please select a pipeline and provide configuration')
      return
    }

    try {
      setValidating(true)
      setError(null)
      const result = await validatePipeline(selectedPipeline, yamlContent)
      setValidationResult(result)
      if (result.valid) {
        setSuccess('Configuration is valid!')
      } else {
        setError('Configuration validation failed')
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to validate configuration')
    } finally {
      setValidating(false)
    }
  }

  const handleSetDefault = async (pipelineName: string) => {
    try {
      await setDefaultPipeline(pipelineName)
      setSuccess(`Pipeline '${pipelineName}' set as default`)
      await loadPipelines()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to set default pipeline')
    }
  }

  return (
    <div className="config-manager">
      <div className="config-header">
        <h2>Pipeline Configuration</h2>
        <div className="config-actions">
          <button
            className="btn btn-primary"
            onClick={handleCreate}
            disabled={saving}
          >
            Create Pipeline
          </button>
        </div>
      </div>

      <div className="config-content">
        <div className="config-sidebar">
          <div className="sidebar-header-section">
            <h3>Pipelines</h3>
            <button
              className="btn btn-primary btn-small"
              onClick={handleCreate}
              disabled={saving}
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
                    onClick={() => setSelectedPipeline(pipeline)}
                  >
                    <span className="pipeline-name">{pipeline}</span>
                    {pipeline === pipelines.default && (
                      <span className="default-badge">default</span>
                    )}
                    {pipeline === pipelines.default ? (
                      <span
                        className="set-default-btn disabled"
                        title="Already default"
                      >
                        ★
                      </span>
                    ) : (
                      <span
                        className="set-default-btn"
                        onClick={(e) => {
                          e.stopPropagation()
                          handleSetDefault(pipeline)
                        }}
                        title="Set as default"
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

        <div className="config-editor">
          {selectedPipeline ? (
            <>
              {loading ? (
                <div className="loading">Loading configuration...</div>
              ) : (
                <>
                  <PipelineFlowchart config={parsedConfig} />
                  <div className="editor-toolbar">
                    <h3 className="editor-title">Editing: {selectedPipeline}</h3>
                    <div className="editor-actions">
                      <button
                        className="btn btn-secondary btn-small"
                        onClick={handleValidate}
                        disabled={validating || !yamlContent.trim()}
                      >
                        {validating ? 'Validating...' : 'Validate'}
                      </button>
                      <button
                        className="btn btn-primary btn-small"
                        onClick={handleSave}
                        disabled={saving || !yamlContent.trim()}
                      >
                        {saving ? 'Saving...' : 'Save'}
                      </button>
                      <button
                        className="btn btn-danger btn-small"
                        onClick={handleDelete}
                        disabled={saving}
                      >
                        Delete
                      </button>
                    </div>
                  </div>
                  <textarea
                    className="yaml-editor"
                    value={yamlContent}
                    onChange={(e) => setYamlContent(e.target.value)}
                    placeholder="Enter YAML configuration..."
                    spellCheck={false}
                  />
                  {validationResult && (
                    <div className={`validation-result ${validationResult.valid ? 'valid' : 'invalid'}`}>
                      <strong>Validation:</strong>{' '}
                      {validationResult.valid ? (
                        <span className="valid-text">✓ Configuration is valid</span>
                      ) : (
                        <div className="invalid-text">
                          <span>✗ Configuration has errors:</span>
                          <pre>{JSON.stringify(validationResult.errors, null, 2)}</pre>
                        </div>
                      )}
                    </div>
                  )}
                </>
              )}
            </>
          ) : (
            <div className="no-selection">
              <p>Select a pipeline from the list to edit its configuration, or create a new pipeline.</p>
            </div>
          )}
        </div>
      </div>

      {error && (
        <div className="error-message">
          <strong>Error:</strong> {error}
        </div>
      )}

      {success && (
        <div className="success-message">
          <strong>Success:</strong> {success}
        </div>
      )}
    </div>
  )
}

export default ConfigManager

