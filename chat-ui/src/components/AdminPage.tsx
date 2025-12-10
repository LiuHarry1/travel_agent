import { useState, useEffect } from 'react'
import { 
  getProviders, 
  getLLMConfig, 
  getAvailableModels, 
  updateLLMConfig, 
  getDefaultConfig,
  saveConfig,
  getFunctionCalls,
  updateFunctionCalls,
  updateSystemPrompt,
  type ProviderInfo,
  type FunctionDefinition
} from '../api/index'
import { Alert } from './Alert'

type TabType = 'llm' | 'prompt' | 'functions'

export function AdminPage() {
  const [activeTab, setActiveTab] = useState<TabType>('llm')
  
  // LLM Config state
  const [providers, setProviders] = useState<ProviderInfo[]>([])
  const [provider, setProvider] = useState<string>('')
  const [model, setModel] = useState<string>('')
  const [openaiBaseUrl, setOpenaiBaseUrl] = useState<string>('')
  const [availableModels, setAvailableModels] = useState<string[]>([])
  const [loading, setLoading] = useState(false)
  const [loadingProviders, setLoadingProviders] = useState(false)
  const [loadingModels, setLoadingModels] = useState(false)
  
  // System Prompt state
  const [systemPrompt, setSystemPrompt] = useState<string>('')
  const [loadingPrompt, setLoadingPrompt] = useState(false)
  const [savingPrompt, setSavingPrompt] = useState(false)
  
  // Function Calls state
  const [functions, setFunctions] = useState<FunctionDefinition[]>([])
  const [enabledFunctions, setEnabledFunctions] = useState<string[]>([])
  const [loadingFunctions, setLoadingFunctions] = useState(false)
  const [savingFunctions, setSavingFunctions] = useState(false)
  
  const [alert, setAlert] = useState<{ type: 'error' | 'success'; message: string } | null>(null)

  // Load providers and current configuration
  useEffect(() => {
    loadProviders()
    loadConfig()
    loadSystemPrompt()
    loadFunctionCalls()
  }, [])

  // Load available models when provider changes
  useEffect(() => {
    if (provider) {
      loadModels()
    }
  }, [provider])

  const loadProviders = async () => {
    try {
      setLoadingProviders(true)
      const response = await getProviders()
      setProviders(response.providers)
    } catch (error) {
      setAlert({
        type: 'error',
        message: error instanceof Error ? error.message : 'Failed to load providers',
      })
    } finally {
      setLoadingProviders(false)
    }
  }

  const loadConfig = async () => {
    try {
      setLoading(true)
      const config = await getLLMConfig()
      setProvider(config.provider)
      setModel(config.model)
      
      // Set provider-specific URLs from config or use defaults
      if (config.provider === 'openai') {
        setOpenaiBaseUrl(config.openai_base_url || '')
      }
    } catch (error) {
      setAlert({
        type: 'error',
        message: error instanceof Error ? error.message : 'Failed to load configuration',
      })
    } finally {
      setLoading(false)
    }
  }

  const loadModels = async () => {
    if (!provider) return

    try {
      setLoadingModels(true)
      
      // Fetch models from backend API
      const response = await getAvailableModels(provider)
      setAvailableModels(response.models || [])
      
      // If current model is not in the list, keep it
      if (model && response.models && !response.models.includes(model)) {
        // Keep current model
      } else if (response.models && response.models.length > 0 && !model) {
        setModel(response.models[0])
      }
    } catch (error) {
      setAlert({
        type: 'error',
        message: error instanceof Error ? error.message : 'Failed to load available models',
      })
      setAvailableModels([])
    } finally {
      setLoadingModels(false)
    }
  }

  const handleUpdate = async () => {
    if (!provider || !model) {
      setAlert({
        type: 'error',
        message: 'Please select both provider and model',
      })
      return
    }

    try {
      setLoading(true)
      await updateLLMConfig({
        provider,
        model,
        openai_base_url: provider === 'openai' ? openaiBaseUrl : undefined,
      })
      setAlert({
        type: 'success',
        message: 'Configuration updated successfully! The new model will be used for future requests.',
      })
    } catch (error) {
      setAlert({
        type: 'error',
        message: error instanceof Error ? error.message : 'Failed to update configuration',
      })
    } finally {
      setLoading(false)
    }
  }

  const handleProviderChange = (newProvider: string) => {
    setProvider(newProvider)
    setModel('') // Reset model when provider changes
  }

  const handleOpenaiBaseUrlChange = (newUrl: string) => {
    setOpenaiBaseUrl(newUrl)
  }

  const loadSystemPrompt = async () => {
    try {
      setLoadingPrompt(true)
      const config = await getDefaultConfig()
      setSystemPrompt(config.system_prompt_template || '')
    } catch (error) {
      setAlert({
        type: 'error',
        message: error instanceof Error ? error.message : 'Failed to load system prompt',
      })
    } finally {
      setLoadingPrompt(false)
    }
  }

  const handleSaveSystemPrompt = async () => {
    if (!systemPrompt.trim()) {
      setAlert({
        type: 'error',
        message: 'System prompt template cannot be empty',
      })
      return
    }

    try {
      setSavingPrompt(true)
      // Try new API first, fallback to old API
      try {
        await updateSystemPrompt({ prompt: systemPrompt })
        setAlert({
          type: 'success',
          message: 'System prompt updated successfully! The new prompt will be used for future conversations.',
        })
      } catch {
        await saveConfig({
          system_prompt_template: systemPrompt,
        })
        setAlert({
          type: 'success',
          message: 'System prompt template updated successfully! The new template will be used for future conversations.',
        })
      }
    } catch (error) {
      setAlert({
        type: 'error',
        message: error instanceof Error ? error.message : 'Failed to save system prompt template',
      })
    } finally {
      setSavingPrompt(false)
    }
  }

  const loadFunctionCalls = async () => {
    try {
      setLoadingFunctions(true)
      const response = await getFunctionCalls()
      setFunctions(response.available_functions)
      setEnabledFunctions(response.enabled_functions)
    } catch (error) {
      setAlert({
        type: 'error',
        message: error instanceof Error ? error.message : 'Failed to load function calls',
      })
    } finally {
      setLoadingFunctions(false)
    }
  }

  const handleSaveFunctionCalls = async () => {
    try {
      setSavingFunctions(true)
      await updateFunctionCalls({
        enabled_functions: enabledFunctions,
        configs: {}
      })
      setAlert({
        type: 'success',
        message: 'Function calls updated successfully! The new functions will be available for future conversations.',
      })
      await loadFunctionCalls()
    } catch (error) {
      setAlert({
        type: 'error',
        message: error instanceof Error ? error.message : 'Failed to save function calls',
      })
    } finally {
      setSavingFunctions(false)
    }
  }


  return (
    <section className="admin-container">
      <div className="admin-header">
        <h1>Admin Settings</h1>
        <p className="admin-subtitle">Configure LLM, system prompt, and function calls</p>
      </div>

      {alert && (
        <Alert
          type={alert.type}
          message={alert.message}
          onClose={() => setAlert(null)}
        />
      )}

      {/* Tabs */}
      <div className="admin-tabs">
        <button
          type="button"
          className={`admin-tab ${activeTab === 'llm' ? 'active' : ''}`}
          onClick={() => setActiveTab('llm')}
        >
          LLM Configuration
        </button>
        <button
          type="button"
          className={`admin-tab ${activeTab === 'prompt' ? 'active' : ''}`}
          onClick={() => setActiveTab('prompt')}
        >
          System Prompt
        </button>
        <button
          type="button"
          className={`admin-tab ${activeTab === 'functions' ? 'active' : ''}`}
          onClick={() => setActiveTab('functions')}
        >
          Function Calls
        </button>
      </div>

      <div className="admin-content">
        {/* LLM Configuration Tab */}
        {activeTab === 'llm' && (
          <>
            <div className="admin-form">
              <div className="form-group">
                <label htmlFor="provider">Provider</label>
                <select
                  id="provider"
                  value={provider}
                  onChange={(e) => handleProviderChange(e.target.value)}
                  disabled={loading || loadingProviders}
                  className="form-select"
                >
                  <option value="">Select a provider</option>
                  {providers.map((p) => (
                    <option key={p.value} value={p.value}>
                      {p.label}
                    </option>
                  ))}
                </select>
              </div>

              {provider === 'openai' && (
                <div className="form-group">
                  <label htmlFor="openai-base-url">OpenAI Base URL</label>
                  <input
                    id="openai-base-url"
                    type="text"
                    value={openaiBaseUrl}
                    onChange={(e) => handleOpenaiBaseUrlChange(e.target.value)}
                    placeholder="https://api.openai.com/v1 or http://10.150.117.242:33148/v1"
                    disabled={loading}
                    className="form-input"
                  />
                  <small className="form-hint">
                    Enter the base URL for OpenAI API or OpenAI-compatible proxy server. 
                    Defaults to https://api.openai.com/v1 if not specified. 
                    For proxy servers, include /v1 at the end (e.g., http://10.150.117.242:33148/v1).
                  </small>
                </div>
              )}

              <div className="form-group">
                <label htmlFor="model">Model</label>
                <select
                  id="model"
                  value={model}
                  onChange={(e) => setModel(e.target.value)}
                  disabled={loading || !provider || availableModels.length === 0}
                  className="form-select"
                >
                  <option value="">Select a model</option>
                  {availableModels.map((m) => (
                    <option key={m} value={m}>
                      {m}
                    </option>
                  ))}
                </select>
                {provider && availableModels.length === 0 && !loadingModels && (
                  <small className="form-error">
                    No models available. Please select a provider.
                  </small>
                )}
              </div>

              <div className="form-actions">
                <button
                  type="button"
                  onClick={handleUpdate}
                  disabled={loading || !provider || !model}
                  className="btn btn-primary"
                >
                  {loading ? 'Updating...' : 'Update Configuration'}
                </button>
              </div>
            </div>

            <div className="admin-info">
              <h3>Current Configuration</h3>
              <div className="info-card">
                <div className="info-row">
                  <span className="info-label">Provider:</span>
                  <span className="info-value">{provider || 'Not set'}</span>
                </div>
                <div className="info-row">
                  <span className="info-label">Model:</span>
                  <span className="info-value">{model || 'Not set'}</span>
                </div>
                {provider === 'openai' && (
                  <div className="info-row">
                    <span className="info-label">OpenAI Base URL:</span>
                    <span className="info-value">{openaiBaseUrl || 'https://api.openai.com/v1 (default)'}</span>
                  </div>
                )}
              </div>

              <div className="info-note">
                <p>
                  <strong>Note:</strong> After updating the configuration, all new chat and review requests will use the selected model.
                </p>
              </div>
            </div>
          </>
        )}

        {/* System Prompt Tab */}
        {activeTab === 'prompt' && (
          <>
            <div className="admin-form" style={{ gridColumn: '1 / -1' }}>
              <div className="form-group">
                <label htmlFor="system-prompt">System Prompt Template</label>
                {loadingPrompt ? (
                  <div className="form-loading">Loading system prompt template...</div>
                ) : (
                  <textarea
                    id="system-prompt"
                    value={systemPrompt}
                    onChange={(e) => setSystemPrompt(e.target.value)}
                    disabled={savingPrompt}
                    className="form-textarea"
                    rows={15}
                    placeholder="You are a helpful travel agent assistant. Your goal is to help users with travel-related questions and planning.&#10;&#10;Available Tools:&#10;{tools}&#10;&#10;Instructions:&#10;- Use tools when you need specific information to answer questions&#10;- Base your answers STRICTLY on tool results&#10;- Do not add information not in tool results"
                  />
                )}
                <small className="form-hint">
                  Enter the system prompt template. Use <code>{'{tools}'}</code> placeholder to insert the available tools list. 
                  If <code>{'{tools}'}</code> is not present, tools will be automatically appended at the end.
                </small>
              </div>

              <div className="form-actions">
                <button
                  type="button"
                  onClick={handleSaveSystemPrompt}
                  disabled={savingPrompt || loadingPrompt || !systemPrompt.trim()}
                  className="btn btn-primary"
                >
                  {savingPrompt ? 'Saving...' : 'Save System Prompt Template'}
                </button>
              </div>
            </div>

            <div className="admin-info" style={{ gridColumn: '1 / -1' }}>
              <h3>Template Info</h3>
              <div className="info-card">
                <div className="info-row">
                  <span className="info-label">Length:</span>
                  <span className="info-value">{systemPrompt.length} characters</span>
                </div>
                <div className="info-row">
                  <span className="info-label">Contains {'{tools}'} placeholder:</span>
                  <span className="info-value">{systemPrompt.includes('{tools}') ? 'Yes' : 'No (tools will be appended)'}</span>
                </div>
              </div>
              <div className="info-note">
                <p>
                  <strong>Note:</strong> The <code>{'{tools}'}</code> placeholder will be replaced with the list of available tools when the system prompt is generated. 
                  If you don't include the placeholder, tools will be automatically added at the end. Changes take effect immediately for new conversations.
                </p>
              </div>
            </div>
          </>
        )}

        {/* Function Calls Tab */}
        {activeTab === 'functions' && (
          <>
            <div className="admin-form" style={{ gridColumn: '1 / -1' }}>
              <div className="function-calls-header">
                <h3>Function Calls Management</h3>
                <p className="function-calls-description">
                  Select which functions are enabled for the agent. When <strong>retrieval_service_search</strong> is enabled, 
                  the agent will automatically use <strong>RAG mode</strong> with context-aware query generation and multi-turn retrieval.
                </p>
              </div>
              
              {loadingFunctions ? (
                <div className="form-loading">Loading functions...</div>
              ) : (
                <div className="function-cards">
                  {functions.map((func) => {
                    const isEnabled = enabledFunctions.includes(func.name)
                    const isRAGMode = func.name === 'retrieval_service_search' && isEnabled
                    return (
                      <div
                        key={func.name}
                        className={`function-card ${isEnabled ? 'function-card-enabled' : 'function-card-disabled'}`}
                      >
                        <div className="function-card-header">
                          <label className="function-toggle">
                            <input
                              type="checkbox"
                              checked={isEnabled}
                              onChange={(e) => {
                                if (e.target.checked) {
                                  setEnabledFunctions([...enabledFunctions, func.name])
                                } else {
                                  setEnabledFunctions(enabledFunctions.filter(f => f !== func.name))
                                }
                              }}
                            />
                            <span className="function-checkmark"></span>
                          </label>
                          <div className="function-title-section">
                            <h4 className="function-name">{func.name}</h4>
                            <div className="function-badges">
                              <span className={`function-badge function-badge-${func.type === 'external_api' ? 'external' : 'local'}`}>
                                {func.type === 'external_api' ? 'External API' : 'Local'}
                              </span>
                              {isRAGMode && (
                                <span className="function-badge function-badge-rag">
                                  <span className="rag-indicator">●</span> RAG Mode
                                </span>
                              )}
                            </div>
                          </div>
                        </div>
                        <p className="function-description">{func.description}</p>
                        {func.config && Object.keys(func.config).length > 0 && (
                          <details className="function-config">
                            <summary className="function-config-summary">
                              <span>Configuration</span>
                              <span className="function-config-icon">▼</span>
                            </summary>
                            <div className="function-config-content">
                              {Object.entries(func.config).map(([key, value]) => (
                                <div key={key} className="function-config-item">
                                  <span className="function-config-key">{key}:</span>
                                  <span className="function-config-value">
                                    {typeof value === 'object' ? JSON.stringify(value) : String(value)}
                                  </span>
                                </div>
                              ))}
                            </div>
                          </details>
                        )}
                      </div>
                    )
                  })}
                </div>
              )}

              <div className="form-actions" style={{ marginTop: '24px' }}>
                <button
                  type="button"
                  onClick={handleSaveFunctionCalls}
                  disabled={savingFunctions || loadingFunctions}
                  className="btn btn-primary"
                >
                  {savingFunctions ? 'Saving...' : 'Save Function Configuration'}
                </button>
              </div>
            </div>

            <div className="admin-info" style={{ gridColumn: '1 / -1' }}>
              <h3>Current Function Configuration</h3>
              <div className="info-card">
                <div className="info-row">
                  <span className="info-label">Total Functions:</span>
                  <span className="info-value">{functions.length}</span>
                </div>
                <div className="info-row">
                  <span className="info-label">Enabled Functions:</span>
                  <span className="info-value">{enabledFunctions.length}</span>
                </div>
              </div>
              <div className="info-note">
                <p>
                  <strong>Note:</strong> After updating the function configuration, the agent will use the new 
                  function set for future conversations. If retrieval_service_search is enabled, the agent will 
                  automatically use RAG mode with context-aware query generation.
                </p>
              </div>
            </div>
          </>
        )}
      </div>
    </section>
  )
}

