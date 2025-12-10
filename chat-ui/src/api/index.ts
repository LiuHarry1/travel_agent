/**
 * Main API module - re-exports all API functions
 */

// Chat API
export { sendChatMessageStream } from './chat'

// Title API
export { generateTitle } from './title'

// Config API
export { getDefaultConfig, saveConfig } from './config'
export type { ConfigResponse, SaveConfigPayload, SaveConfigResponse } from './config'

// File API
export { uploadFile } from './file'
export type { FileUploadResponse } from './file'

// Admin API
export {
  getProviders,
  getLLMConfig,
  getAvailableModels,
  updateLLMConfig,
  getFunctionCalls,
  updateFunctionCalls,
  updateSystemPrompt,
} from './admin'
export type {
  ProviderInfo,
  ProvidersResponse,
  LLMConfigResponse,
  ModelsResponse,
  UpdateLLMConfigRequest,
  UpdateLLMConfigResponse,
  FunctionDefinition,
  FunctionCallsResponse,
  FunctionCallsUpdateRequest,
  SystemPromptUpdateRequest,
} from './admin'

