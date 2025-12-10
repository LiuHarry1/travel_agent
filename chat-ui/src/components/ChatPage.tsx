/**
 * Chat page component
 * Main container for chat interface
 */

import { useEffect, useRef, useState, useCallback, type FormEvent } from 'react'
import { useChat } from '../hooks/useChat'
import { useFileUpload } from '../hooks/useFileUpload'
import { uploadFile } from '../api'
import { MessageList } from './MessageList'
import { ChatInput } from './ChatInput'
import { EmptyChatState } from './EmptyChatState'
import type { FileWithContent } from './FileUploadPreview'
import { SCROLL_PADDING, SCROLL_DELAY, STREAM_END_SCROLL_DELAY, SCROLL_CONTENT_THRESHOLD, AUTO_SCROLL_THRESHOLD } from '../constants'

export function ChatPage() {
  const {
    message,
    setMessage,
    history,
    loading,
    alert,
    setAlert,
    sendMessage,
    stopGeneration,
    regenerateResponse,
  } = useChat()

  const {
    uploadedFiles,
    dragOver,
    fileInputRef,
    handleDragOver,
    handleDragLeave,
    handleDrop,
    handleFileSelect,
    removeFile,
    clearFiles,
    openFileDialog,
    formatErrorMessages,
  } = useFileUpload()

  const [filesWithContent, setFilesWithContent] = useState<FileWithContent[]>([])

  // Upload files to backend immediately when they're added
  useEffect(() => {
    const uploadFiles = async () => {
      const newFiles = uploadedFiles.filter(
        (file) => !filesWithContent.find((fwc) => fwc.file === file)
      )

      if (newFiles.length === 0) return

      // Immediately add new files with loading state
      setFilesWithContent((prev) => {
        const newFilesWithContent = newFiles.map((file) => ({ 
          file, 
          loading: true, 
          progress: 0 
        }))
        return [...prev, ...newFilesWithContent]
      })

      // Upload each new file immediately
      for (const file of newFiles) {
        try {
          const result = await uploadFile(
            file,
            (progress) => {
              // Update progress in real-time
              setFilesWithContent((prev) =>
                prev.map((fwc) =>
                  fwc.file === file ? { ...fwc, progress } : fwc
                )
              )
            }
          )
          setFilesWithContent((prev) =>
            prev.map((fwc) =>
              fwc.file === file 
                ? { file, content: result.content, loading: false, progress: 100 } 
                : fwc
            )
          )
        } catch (error) {
          const errorMessage = error instanceof Error ? error.message : 'Upload failed'
          setFilesWithContent((prev) =>
            prev.map((fwc) =>
              fwc.file === file 
                ? { file, loading: false, error: errorMessage, progress: 0 } 
                : fwc
            )
          )
          setAlert({ type: 'error', message: `Failed to upload ${file.name}: ${errorMessage}` })
        }
      }
    }

    uploadFiles()
    // Remove filesWithContent from dependencies to avoid circular updates
    // We only want to trigger when uploadedFiles changes
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [uploadedFiles, setAlert])

  // Sync with uploadedFiles (remove if removed from uploadedFiles)
  useEffect(() => {
    setFilesWithContent((prev) => prev.filter((fwc) => uploadedFiles.includes(fwc.file)))
  }, [uploadedFiles])

  const textareaRef = useRef<HTMLTextAreaElement>(null)
  const messagesWrapperRef = useRef<HTMLDivElement>(null)
  const latestUserMessageRef = useRef<HTMLDivElement>(null)
  const [autoScroll, setAutoScroll] = useState(true)

  // Define hasHistory before useEffects
  const hasHistory = history.length > 0

  // When starting a new empty chat, scroll to top and focus textarea
  useEffect(() => {
    if (!loading && history.length === 0) {
      if (messagesWrapperRef.current) {
        messagesWrapperRef.current.scrollTop = 0
      }
      if (textareaRef.current) {
        textareaRef.current.focus()
      }
    }
  }, [history.length, loading])

  // Track state for scroll behavior
  const userMessageCountRef = useRef(0)
  const hasMountedRef = useRef(false)
  const wasLoadingRef = useRef(false)

  // ChatGPT-style scroll behavior:
  // 1. When user sends new message -> scroll to put user message at top (CSS min-height handles the rest)
  // 2. During streaming -> auto-scroll to bottom when content exceeds viewport
  // 3. When streaming ends -> scroll to bottom to show action icons
  useEffect(() => {
    if (!hasHistory) return

    const container = messagesWrapperRef.current
    if (!container) return

    const currentUserCount = history.reduce((count, turn) => count + (turn.role === 'user' ? 1 : 0), 0)
    const hasNewUserMessage = hasMountedRef.current && currentUserCount > userMessageCountRef.current
    const streamingJustEnded = !loading && wasLoadingRef.current

    if (hasNewUserMessage) {
      // User just sent a new message
      // Enable auto-scroll and scroll to user message position
      setAutoScroll(true)
      
      // Wait for DOM to update, then scroll to user message
      setTimeout(() => {
        const messageElement = latestUserMessageRef.current
        if (!messageElement || !container) return

        // Scroll so user message is near the top with some padding
        const targetScrollTop = Math.max(0, messageElement.offsetTop - SCROLL_PADDING)
        container.scrollTo({
          top: targetScrollTop,
          behavior: 'smooth',
        })
      }, SCROLL_DELAY)
    } else if (loading && autoScroll) {
      // During streaming: scroll to bottom when content exceeds viewport
      requestAnimationFrame(() => {
        if (!container) return
        const distanceToBottom = container.scrollHeight - container.scrollTop - container.clientHeight
        // Only scroll if there's significant content below viewport
        if (distanceToBottom > SCROLL_CONTENT_THRESHOLD) {
          container.scrollTop = container.scrollHeight
        }
      })
    } else if (streamingJustEnded && autoScroll) {
      // Streaming just ended - scroll to bottom to show action icons
      setTimeout(() => {
        if (container) {
          container.scrollTo({
            top: container.scrollHeight,
            behavior: 'smooth',
          })
        }
      }, STREAM_END_SCROLL_DELAY)
    }

    // Update refs
    wasLoadingRef.current = loading
    userMessageCountRef.current = currentUserCount
    hasMountedRef.current = true
  }, [history, loading, autoScroll, hasHistory])

  const handleMessagesScroll = () => {
    const container = messagesWrapperRef.current
    if (!container) return
    const distanceToBottom = container.scrollHeight - container.scrollTop - container.clientHeight
    setAutoScroll(distanceToBottom <= AUTO_SCROLL_THRESHOLD)
  }

  const handleSubmit = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault()

    // Handle file upload if files are present
    const readyFiles = filesWithContent.filter((fwc) => fwc.content && !fwc.loading && !fwc.error)
    
    if (readyFiles.length > 0) {
      try {
        // Send message with file contents (filename and content)
        const filesData = readyFiles.map((fwc) => ({
          name: fwc.file.name,
          content: fwc.content!,
        }))

        // Clear input and files immediately before sending
        setMessage('')
        clearFiles()
        setFilesWithContent([])

        // Send message (don't await, let it stream in background)
        sendMessage(message.trim() || undefined, filesData).catch((error) => {
          const errorMessage = error instanceof Error ? error.message : 'Send failed'
          setAlert({ type: 'error', message: errorMessage })
        })
      } catch (error) {
        const errorMessage = error instanceof Error ? error.message : 'Send failed'
        setAlert({ type: 'error', message: errorMessage })
      }
      return
    }

    // Check if there are files still loading
    if (filesWithContent.some((fwc) => fwc.loading)) {
      setAlert({ type: 'error', message: 'Please wait for files to finish uploading' })
      return
    }

    // Check if there are files with errors
    const errorFiles = filesWithContent.filter((fwc) => fwc.error)
    if (errorFiles.length > 0) {
      setAlert({ type: 'error', message: 'Some files failed to upload. Please remove them and try again.' })
      return
    }

    // Handle text message only
    if (message.trim()) {
      // Clear input immediately before sending
      const messageToSend = message.trim()
      setMessage('')
      
      // Send message (don't await, let it stream in background)
      sendMessage(messageToSend).catch((error) => {
        const errorMessage = error instanceof Error ? error.message : 'Send failed'
        setAlert({ type: 'error', message: errorMessage })
      })
    }
  }

  const handleDropWithValidation = (e: React.DragEvent<HTMLElement>) => {
    // Convert to HTMLDivElement for useFileUpload handler
    const errors = handleDrop(e as React.DragEvent<HTMLDivElement>)
    if (errors.length > 0) {
      const errorMessage = formatErrorMessages(errors)
      setAlert({ type: 'error', message: errorMessage })
    }
  }

  // Wrapper functions to convert drag event types
  const handleDragOverWrapper = useCallback((e: React.DragEvent<HTMLElement>) => {
    handleDragOver(e as unknown as React.DragEvent<HTMLDivElement>)
  }, [handleDragOver])

  const handleDragLeaveWrapper = useCallback((e: React.DragEvent<HTMLElement>) => {
    handleDragLeave(e as unknown as React.DragEvent<HTMLDivElement>)
  }, [handleDragLeave])

  return (
    <section className={`chat-container ${hasHistory ? '' : 'chat-container-initial'}`}>
      {hasHistory ? (
        <>
          {/* Chat Messages Area */}
          <div
            className="chat-messages-wrapper"
            ref={messagesWrapperRef}
            onScroll={handleMessagesScroll}
          >
            <MessageList
              history={history}
              loading={loading}
              latestUserMessageRef={latestUserMessageRef}
              onRegenerate={regenerateResponse}
            />
          </div>

          {/* Chat Input Area */}
          <div className="chat-input-container-wrapper">
            <ChatInput
              message={message}
              setMessage={setMessage}
              loading={loading}
              filesWithContent={filesWithContent}
              uploadedFiles={uploadedFiles}
              dragOver={dragOver}
              fileInputRef={fileInputRef}
              onDragOver={handleDragOverWrapper}
              onDragLeave={handleDragLeaveWrapper}
              onDrop={handleDropWithValidation}
              onFileSelect={handleFileSelect}
              onRemoveFile={removeFile}
              onSubmit={handleSubmit}
              onStop={stopGeneration}
              openFileDialog={openFileDialog}
              alert={alert}
            />
          </div>
        </>
      ) : (
        <div className="chat-initial-layout">
          <div className="chat-initial-inner">
            {history.length === 0 ? (
              <EmptyChatState />
            ) : (
              <MessageList
                history={history}
                loading={loading}
                latestUserMessageRef={latestUserMessageRef}
                onRegenerate={regenerateResponse}
              />
            )}
            <div className="chat-input-floating">
              <ChatInput
                message={message}
                setMessage={setMessage}
                loading={loading}
                filesWithContent={filesWithContent}
                uploadedFiles={uploadedFiles}
                dragOver={dragOver}
                fileInputRef={fileInputRef}
                onDragOver={handleDragOverWrapper}
                onDragLeave={handleDragLeaveWrapper}
                onDrop={handleDropWithValidation}
                onFileSelect={handleFileSelect}
                onRemoveFile={removeFile}
                onSubmit={handleSubmit}
                onStop={stopGeneration}
                openFileDialog={openFileDialog}
                alert={alert}
              />
            </div>
          </div>
        </div>
      )}
    </section>
  )
}
