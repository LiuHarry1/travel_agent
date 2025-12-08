import { useState, useEffect, useCallback } from 'react'
import { getPipelines, setDefaultPipeline, type PipelineList } from '../api/config'
import { handleApiError } from '../utils/errorHandler'

interface UsePipelinesReturn {
  pipelines: PipelineList
  loading: boolean
  error: string | null
  refresh: () => Promise<void>
  setDefault: (pipelineName: string) => Promise<void>
}

/**
 * 管理 pipelines 列表的自定义 Hook
 */
export function usePipelines(): UsePipelinesReturn {
  const [pipelines, setPipelines] = useState<PipelineList>({ default: null, pipelines: [] })
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const loadPipelines = useCallback(async () => {
    try {
      setLoading(true)
      setError(null)
      const data = await getPipelines()
      setPipelines(data)
    } catch (err) {
      const errorMessage = handleApiError('Failed to load pipelines', err)
      setError(errorMessage)
    } finally {
      setLoading(false)
    }
  }, [])

  const refresh = useCallback(async () => {
    await loadPipelines()
  }, [loadPipelines])

  const setDefault = useCallback(
    async (pipelineName: string) => {
      try {
        setError(null)
        await setDefaultPipeline(pipelineName)
        await loadPipelines()
      } catch (err) {
        const errorMessage = handleApiError('Failed to set default pipeline', err)
        setError(errorMessage)
        throw err
      }
    },
    [loadPipelines]
  )

  useEffect(() => {
    loadPipelines()
  }, [loadPipelines])

  return {
    pipelines,
    loading,
    error,
    refresh,
    setDefault,
  }
}

