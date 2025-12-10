/**
 * Application constants
 * Centralized location for all magic numbers and strings
 */

// Session related constants
export const DEFAULT_SESSION_TITLE = 'New chat'
export const MAX_SESSIONS = 10
export const CHAT_SESSIONS_STORAGE_KEY = 'chat-ui-sessions-v2'
export const LEGACY_CHAT_STORAGE_KEY = 'chat-ui-session'

// File upload constants
export const MAX_FILE_SIZE = 5 * 1024 * 1024 // 5MB
export const VALID_FILE_EXTENSIONS = ['.txt', '.md', '.json', '.text', '.pdf', '.doc', '.docx']

// API constants
export const DEFAULT_API_BASE_URL = 'http://localhost:8001'
export const SSE_EVENT_PREFIX = 'data: '

// UI constants
export const AUTO_SCROLL_THRESHOLD = 40 // px
export const TEXTAREA_MAX_HEIGHT = 200 // px
export const SCROLL_PADDING = 16 // px
export const SCROLL_DELAY = 50 // ms
export const STREAM_END_SCROLL_DELAY = 150 // ms
export const SCROLL_CONTENT_THRESHOLD = 100 // px

// Image URL pattern for markdown conversion
export const IMAGE_URL_PATTERN = /(https?:\/\/[^\s]+\.(png|jpg|jpeg|gif|webp|svg|bmp))(?![)\]])/gi
export const DEFAULT_IMAGE_ALT_TEXT = '图片'
