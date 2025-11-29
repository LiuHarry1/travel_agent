export interface ChecklistItem {
  id: string
  description: string
}

export interface Alert {
  type: 'error' | 'success'
  message: string
}

export type ConversationState = 'ready'

export interface ToolCall {
  id?: string
  name: string
  arguments: Record<string, unknown>
  status?: 'calling' | 'completed' | 'error'
  result?: unknown
  error?: string
}

export interface ChatTurn {
  role: 'user' | 'assistant'
  content: string
  toolCalls?: ToolCall[]
}

export interface ChatResponse {
  session_id: string
  state: ConversationState
  replies: string[]
  history: ChatTurn[]
}

export interface ChatPayload {
  session_id?: string
  message?: string
  messages?: Array<{ role: string; content: string }>
  files?: Array<{ name: string; content: string }>
}

export type StreamEventType = 
  | 'chunk' 
  | 'tool_call_start' 
  | 'tool_call_end' 
  | 'tool_call_error' 
  | 'done' 
  | 'error'

export interface StreamEvent {
  type: StreamEventType
  content?: string
  tool?: string
  input?: unknown
  result?: unknown
  error?: string
  tool_call_id?: string
}

export interface Suggestion {
  checklist_id: string
  message: string
}
