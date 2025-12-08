import { useState, useCallback } from 'react'
import {
  getPipeline,
  createPipeline,
  updatePipeline,
  deletePipeline,
  validatePipeline,
  type PipelineConfig,
  type ValidationResult,
} from '../api/config'
import { handleApiError } from '../utils/errorHandler'
import { DEFAULT_PIPELINE_TEMPLATE } from '../constants'

interface UsePipelineConfigReturn {
  config: PipelineConfig | null
  loading: boolean
  saving: boolean
  validating: boolean
  error: string | null
  validationResult: ValidationResult | null
  load: (pipelineName: string) => Promise<void>
  save: (pipelineName: string, yaml: string) => Promise<void>
  create: (pipelineName: string, yaml?: string) => Promise<void>
  remove: (pipelineName: string) => Promise<void>
  validate: (pipelineName: string, yaml: string) => Promise<ValidationResult>
  clear: () => void
}

/**
 * 管理单个 pipeline 配置的自定义 Hook
 */
export function usePipelineConfig(): UsePipelineConfigReturn {
  const [config, setConfig] = useState<PipelineConfig | null>(null)
  const [loading, setLoading] = useState(false)
  const [saving, setSaving] = useState(false)
  const [validating, setValidating] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [validationResult, setValidationResult] = useState<ValidationResult | null>(null)

  const load = useCallback(async (pipelineName: string) => {
    try {
      setLoading(true)
      setError(null)
      const data = await getPipeline(pipelineName)
      setConfig(data)
      setValidationResult(null)
    } catch (err) {
      const errorMessage = handleApiError('Failed to load pipeline', err)
      setError(errorMessage)
    } finally {
      setLoading(false)
    }
  }, [])

  const save = useCallback(async (pipelineName: string, yaml: string) => {
    try {
      setSaving(true)
      setError(null)
      setValidationResult(null)

      // Validate before saving
      const validation = await validatePipeline(pipelineName, yaml)
      setValidationResult(validation)

      if (!validation.valid) {
        setError('Configuration validation failed. Please fix the errors before saving.')
        return
      }

      // Save configuration
      await updatePipeline(pipelineName, yaml)
      await load(pipelineName)
    } catch (err) {
      const errorMessage = handleApiError('Failed to save configuration', err)
      setError(errorMessage)
    } finally {
      setSaving(false)
    }
  }, [load])

  const create = useCallback(async (pipelineName: string, yaml?: string) => {
    try {
      setSaving(true)
      setError(null)
      const yamlContent = yaml || DEFAULT_PIPELINE_TEMPLATE
      await createPipeline(pipelineName, yamlContent)
      await load(pipelineName)
    } catch (err) {
      const errorMessage = handleApiError('Failed to create pipeline', err)
      setError(errorMessage)
      throw err
    } finally {
      setSaving(false)
    }
  }, [load])

  const remove = useCallback(async (pipelineName: string) => {
    try {
      setSaving(true)
      setError(null)
      await deletePipeline(pipelineName)
      setConfig(null)
      setValidationResult(null)
    } catch (err) {
      const errorMessage = handleApiError('Failed to delete pipeline', err)
      setError(errorMessage)
    } finally {
      setSaving(false)
    }
  }, [])

  const validate = useCallback(async (pipelineName: string, yaml: string) => {
    try {
      setValidating(true)
      setError(null)
      const result = await validatePipeline(pipelineName, yaml)
      setValidationResult(result)
      return result
    } catch (err) {
      const errorMessage = handleApiError('Failed to validate configuration', err)
      setError(errorMessage)
      throw err
    } finally {
      setValidating(false)
    }
  }, [])

  const clear = useCallback(() => {
    setConfig(null)
    setValidationResult(null)
    setError(null)
  }, [])

  return {
    config,
    loading,
    saving,
    validating,
    error,
    validationResult,
    load,
    save,
    create,
    remove,
    validate,
    clear,
  }
}

