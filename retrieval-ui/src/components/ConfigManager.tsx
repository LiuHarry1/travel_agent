import { useState, useEffect, useCallback, useMemo } from 'react'
import { usePipelines } from '../hooks/usePipelines'
import { usePipelineConfig } from '../hooks/usePipelineConfig'
import PipelineFlowchart from './PipelineFlowchart'
import PipelineList from './config/PipelineList'
import YamlEditor from './config/YamlEditor'
import ValidationDisplay from './config/ValidationDisplay'
import { UI_TEXT, DEFAULT_PIPELINE_TEMPLATE } from '../constants'
import { parseYaml } from '../utils/yamlParser'
import type { ParsedPipelineConfig } from '../api/config'
import './ConfigManager.css'

function ConfigManager() {
  const { pipelines, loading: pipelinesLoading, error: pipelinesError, refresh, setDefault } = usePipelines()
  const {
    config,
    loading: configLoading,
    saving,
    validating,
    error: configError,
    validationResult,
    load,
    save,
    create,
    remove,
    validate,
    clear,
  } = usePipelineConfig()

  const [selectedPipeline, setSelectedPipeline] = useState<string>('')
  const [yamlContent, setYamlContent] = useState<string>('')
  const [success, setSuccess] = useState<string | null>(null)

  // Initialize selected pipeline
  useEffect(() => {
    if (pipelines.pipelines.length > 0 && !selectedPipeline) {
      setSelectedPipeline(pipelines.default || pipelines.pipelines[0])
    }
  }, [pipelines, selectedPipeline])

  // Load pipeline when selection changes
  useEffect(() => {
    if (selectedPipeline) {
      load(selectedPipeline)
    } else {
      clear()
      setYamlContent('')
    }
  }, [selectedPipeline, load, clear])

  // Update YAML content when config loads
  useEffect(() => {
    if (config) {
      setYamlContent(config.yaml)
    }
  }, [config])

  // Parse YAML for flowchart
  const parsedConfig = useMemo((): ParsedPipelineConfig | null => {
    if (!yamlContent) return null
    try {
      return parseYaml(yamlContent)
    } catch {
      return null
    }
  }, [yamlContent])

  const handleCreate = useCallback(async () => {
    const pipelineName = prompt(UI_TEXT.CONFIG.CREATE_PROMPT)
    if (!pipelineName) return

    if (pipelines.pipelines.includes(pipelineName)) {
      setSuccess(null)
      return
    }

    try {
      await create(pipelineName, DEFAULT_PIPELINE_TEMPLATE)
      setSuccess(`Pipeline '${pipelineName}' ${UI_TEXT.SUCCESS.CREATED.toLowerCase()}`)
      await refresh()
      setSelectedPipeline(pipelineName)
    } catch {
      // Error is handled by hook
    }
  }, [pipelines.pipelines, create, refresh])

  const handleSave = useCallback(async () => {
    if (!selectedPipeline || !yamlContent.trim()) {
      setSuccess(null)
      return
    }

    try {
      await save(selectedPipeline, yamlContent)
      setSuccess(UI_TEXT.SUCCESS.SAVED)
      await refresh()
    } catch {
      // Error is handled by hook
    }
  }, [selectedPipeline, yamlContent, save, refresh])

  const handleDelete = useCallback(async () => {
    if (!selectedPipeline) return

    if (!confirm(`${UI_TEXT.CONFIG.DELETE_CONFIRM} '${selectedPipeline}'?`)) {
      return
    }

    try {
      await remove(selectedPipeline)
      setSuccess(`Pipeline '${selectedPipeline}' ${UI_TEXT.SUCCESS.DELETED.toLowerCase()}`)
      await refresh()
      setSelectedPipeline('')
      setYamlContent('')
    } catch {
      // Error is handled by hook
    }
  }, [selectedPipeline, remove, refresh])

  const handleValidate = useCallback(async () => {
    if (!selectedPipeline || !yamlContent.trim()) {
      setSuccess(null)
      return
    }

    try {
      const result = await validate(selectedPipeline, yamlContent)
      if (result.valid) {
        setSuccess(UI_TEXT.SUCCESS.VALID)
      } else {
        setSuccess(null)
      }
    } catch {
      // Error is handled by hook
    }
  }, [selectedPipeline, yamlContent, validate])

  const handleSetDefault = useCallback(
    async (pipelineName: string) => {
      try {
        await setDefault(pipelineName)
        setSuccess(`Pipeline '${pipelineName}' ${UI_TEXT.SUCCESS.DEFAULT_SET.toLowerCase()}`)
        await refresh()
      } catch {
        // Error is handled by hook
      }
    },
    [setDefault, refresh]
  )

  const error = pipelinesError || configError

  return (
    <div className="config-manager">
      <div className="config-header">
        <h2>Pipeline Configuration</h2>
        <div className="config-actions">
          <button
            className="btn btn-primary"
            onClick={handleCreate}
            disabled={saving}
            aria-label="Create new pipeline"
          >
            Create Pipeline
          </button>
        </div>
      </div>

      <div className="config-content">
        <PipelineList
          pipelines={pipelines}
          selectedPipeline={selectedPipeline}
          onSelect={setSelectedPipeline}
          onSetDefault={handleSetDefault}
          onCreate={handleCreate}
          loading={pipelinesLoading}
        />

        <div className="config-editor">
          {selectedPipeline ? (
            <>
              {configLoading ? (
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
                        aria-label="Validate configuration"
                      >
                        {validating ? 'Validating...' : 'Validate'}
                      </button>
                      <button
                        className="btn btn-primary btn-small"
                        onClick={handleSave}
                        disabled={saving || !yamlContent.trim()}
                        aria-label="Save configuration"
                      >
                        {saving ? 'Saving...' : 'Save'}
                      </button>
                      <button
                        className="btn btn-danger btn-small"
                        onClick={handleDelete}
                        disabled={saving}
                        aria-label="Delete pipeline"
                      >
                        Delete
                      </button>
                    </div>
                  </div>
                  <YamlEditor
                    value={yamlContent}
                    onChange={setYamlContent}
                    disabled={saving || configLoading}
                  />
                  <ValidationDisplay validationResult={validationResult} />
                </>
              )}
            </>
          ) : (
            <div className="no-selection">
              <p>{UI_TEXT.CONFIG.NO_SELECTION}</p>
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
