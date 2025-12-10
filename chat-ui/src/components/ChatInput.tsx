/**
 * Chat input component
 * Handles message input, file upload, and submission
 */

import { useRef, useEffect, memo, useCallback, type FormEvent } from 'react'
import { FileUploadArea } from './FileUploadArea'
import { Alert } from './Alert'
import { FileUploadPreview, type FileWithContent } from './FileUploadPreview'
import { TEXTAREA_MAX_HEIGHT } from '../constants'

interface ChatInputProps {
  message: string
  setMessage: (message: string) => void
  loading: boolean
  filesWithContent: FileWithContent[]
  uploadedFiles: File[]
  dragOver: boolean
  fileInputRef: React.RefObject<HTMLInputElement | null>
  onDragOver: (e: React.DragEvent<HTMLElement>) => void
  onDragLeave: (e: React.DragEvent<HTMLElement>) => void
  onDrop: (e: React.DragEvent<HTMLElement>) => void
  onFileSelect: (e: React.ChangeEvent<HTMLInputElement>) => void
  onRemoveFile: (index: number) => void
  onSubmit: (e: FormEvent<HTMLFormElement>) => void
  onStop: () => void
  openFileDialog: () => void
  alert: { type: 'error' | 'success'; message: string } | null
}

export const ChatInput = memo(function ChatInput({
  message,
  setMessage,
  loading,
  filesWithContent,
  uploadedFiles,
  dragOver,
  fileInputRef,
  onDragOver,
  onDragLeave,
  onDrop,
  onFileSelect,
  onRemoveFile,
  onSubmit,
  onStop,
  openFileDialog,
  alert,
}: ChatInputProps) {
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  // Auto-resize textarea
  useEffect(() => {
    const textarea = textareaRef.current
    if (!textarea) return

    const adjustHeight = () => {
      textarea.style.height = 'auto'
      textarea.style.height = `${Math.min(textarea.scrollHeight, TEXTAREA_MAX_HEIGHT)}px`
    }

    adjustHeight()
    textarea.addEventListener('input', adjustHeight)
    return () => textarea.removeEventListener('input', adjustHeight)
  }, [message])

  const handleKeyDown = useCallback((e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      if (
        !loading &&
        (message.trim() ||
          filesWithContent.filter((fwc) => fwc.content && !fwc.error).length > 0)
      ) {
        onSubmit(e as any)
      }
    }
  }, [loading, message, filesWithContent, onSubmit])

  const handleDragOver = useCallback((e: React.DragEvent<HTMLTextAreaElement>) => {
    // Prevent browser from opening the file when dragged over the textarea
    e.preventDefault()
  }, [])

  const handleDrop = useCallback((e: React.DragEvent<HTMLTextAreaElement>) => {
    // Prevent default navigation and delegate to our validated drop handler
    e.preventDefault()
    // Cast to HTMLElement to match the prop type
    onDrop(e as unknown as React.DragEvent<HTMLElement>)
  }, [onDrop])

  return (
    <FileUploadArea
      uploadedFiles={[]}
      dragOver={dragOver}
      onDragOver={onDragOver}
      onDragLeave={onDragLeave}
      onDrop={onDrop}
      onFileSelect={onFileSelect}
      onRemoveFile={onRemoveFile}
      fileInputRef={fileInputRef}
    >
      <form onSubmit={onSubmit} className="chat-input-form">
        <div className="chat-input-wrapper">
          <FileUploadPreview
            files={filesWithContent}
            uploadedFiles={uploadedFiles}
            onRemoveFile={onRemoveFile}
          />
          <textarea
            ref={textareaRef}
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            placeholder={
              dragOver
                ? 'Release to upload file...'
                : 'Enter message or drag and drop file to upload...'
            }
            rows={3}
            className="chat-textarea"
            disabled={loading}
            onDragOver={handleDragOver}
            onDrop={handleDrop}
            onKeyDown={handleKeyDown}
          />
          <div className="chat-input-actions">
            <button
              type="button"
              onClick={openFileDialog}
              className="attach-button"
              data-tooltip="Upload file"
              aria-label="Upload file"
              disabled={loading}
            >
              <svg
                xmlns="http://www.w3.org/2000/svg"
                width="20"
                height="20"
                viewBox="0 0 24 24"
                fill="currentColor"
                aria-hidden="true"
              >
                <path
                  fillRule="evenodd"
                  clipRule="evenodd"
                  d="M9.035 15.956a1.29 1.29 0 0 0 1.821-.004l6.911-6.911a3.15 3.15 0 0 0 0-4.457l-.034-.034a3.15 3.15 0 0 0-4.456 0l-7.235 7.234a5.031 5.031 0 0 0 7.115 7.115l6.577-6.577a1.035 1.035 0 0 1 1.463 1.464l-6.576 6.577A7.1 7.1 0 0 1 4.579 10.32l7.235-7.234a5.22 5.22 0 0 1 7.382 0l.034.034a5.22 5.22 0 0 1 0 7.383l-6.91 6.91a3.36 3.36 0 0 1-4.741.012l-.006-.005-.012-.011a3.346 3.346 0 0 1 0-4.732L12.76 7.48a1.035 1.035 0 0 1 1.464 1.463l-5.198 5.198a1.277 1.277 0 0 0 0 1.805z"
                />
              </svg>
            </button>
            <button
              type={loading ? 'button' : 'submit'}
              disabled={
                !loading &&
                (!message.trim() &&
                  filesWithContent.filter((fwc) => fwc.content && !fwc.error).length === 0)
              }
              className={loading ? 'stop-button' : 'send-button'}
              data-tooltip={loading ? 'Stop generating' : 'Send (Enter)'}
              aria-label={loading ? 'Stop generating' : 'Send message'}
              onClick={loading ? (e) => { e.preventDefault(); onStop(); } : undefined}
            >
              {loading ? (
                <svg
                  width="18"
                  height="18"
                  viewBox="0 0 24 24"
                  fill="currentColor"
                  xmlns="http://www.w3.org/2000/svg"
                >
                  <rect x="6" y="6" width="12" height="12" rx="1" />
                </svg>
              ) : (
                <svg
                  width="18"
                  height="18"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2.5"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                >
                  <path d="M12 19V5M5 12l7-7 7 7" />
                </svg>
              )}
            </button>
          </div>
        </div>
        {alert && <Alert type={alert.type} message={alert.message} className="alert-toast" />}
      </form>
    </FileUploadArea>
  )
})
