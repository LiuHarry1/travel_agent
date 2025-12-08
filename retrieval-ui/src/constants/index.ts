/**
 * 应用常量定义
 */

// UI 文本常量
export const UI_TEXT = {
  SEARCH: {
    PLACEHOLDER: 'Enter your question...',
    BUTTON: 'Search',
    BUTTON_LOADING: 'Searching...',
    CLEAR: 'Clear',
  },
  PIPELINE: {
    DEFAULT: '(default)',
    SELECT: 'Select pipeline...',
  },
  ERRORS: {
    EMPTY_QUERY: 'Please enter a query',
    LOAD_FAILED: 'Failed to load',
    SAVE_FAILED: 'Failed to save',
    DELETE_FAILED: 'Failed to delete',
    VALIDATE_FAILED: 'Failed to validate',
    UNEXPECTED: 'An unexpected error occurred',
  },
  SUCCESS: {
    SAVED: 'Configuration saved successfully!',
    CREATED: 'created successfully!',
    DELETED: 'deleted successfully!',
    VALID: 'Configuration is valid!',
    DEFAULT_SET: 'set as default',
  },
  CONFIG: {
    CREATE_PROMPT: 'Enter pipeline name:',
    DELETE_CONFIRM: 'Are you sure you want to delete pipeline',
    NO_SELECTION: 'Select a pipeline from the list to edit its configuration, or create a new pipeline.',
  },
} as const

// 时间格式化常量
export const TIME_FORMAT = {
  MICROSECONDS: 'μs',
  MILLISECONDS: 'ms',
  SECONDS: 's',
} as const

// 分数颜色阈值
export const SCORE_THRESHOLDS = {
  EXCELLENT: 0.5,
  GOOD: 1.0,
  MODERATE: 2.0,
} as const

// 分数颜色
export const SCORE_COLORS = {
  EXCELLENT: '#10B981', // green
  GOOD: '#3B82F6', // blue
  MODERATE: '#F59E0B', // orange
  POOR: '#EF4444', // red
} as const

// 文本预览长度
export const TEXT_PREVIEW_LENGTH = 150

// 默认管道配置模板
export const DEFAULT_PIPELINE_TEMPLATE = `milvus:
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

