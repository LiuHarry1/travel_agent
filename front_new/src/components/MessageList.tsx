import { useRef, useLayoutEffect } from 'react'

interface Message {
  role: 'user' | 'assistant'
  content: string
}

interface MessageListProps {
  messages: Message[]
  loading?: boolean
  scrollContainerRef?: React.RefObject<HTMLDivElement>
}

const alignMessageToTop = (messageElement: HTMLElement, container: HTMLElement) => {
  const paddingTop = parseFloat(window.getComputedStyle(container).paddingTop || '0')
  const containerRectTop = container.getBoundingClientRect().top
  const messageRectTop = messageElement.getBoundingClientRect().top
  const distanceToTop = messageRectTop - containerRectTop
  const nextScrollTop = Math.max(container.scrollTop + distanceToTop - paddingTop, 0)

  container.scrollTop = nextScrollTop
  container.scrollTo({ top: nextScrollTop, behavior: 'auto' })
}

export function MessageList({ messages, loading, scrollContainerRef }: MessageListProps) {
  const latestUserMessageRef = useRef<HTMLDivElement>(null)
  const messagesContainerRef = useRef<HTMLDivElement>(null)
  const prevUserMessageCountRef = useRef(0)

  // Find the latest user message index
  const latestUserMessageIndex = messages.length > 0 
    ? messages.map((msg, idx) => ({ msg, idx }))
        .filter(({ msg }) => msg.role === 'user')
        .pop()?.idx ?? -1
    : -1

  // Count user messages to detect new ones
  const userMessageCount = messages.filter(msg => msg.role === 'user').length
  const isNewUserMessage = userMessageCount > prevUserMessageCountRef.current

  // Scroll to top when a new user message is added
  useLayoutEffect(() => {
    const container = scrollContainerRef?.current
    const messageElement = latestUserMessageRef.current

    if (
      !isNewUserMessage ||
      latestUserMessageIndex < 0 ||
      !messageElement ||
      !container
    ) {
      prevUserMessageCountRef.current = userMessageCount
      return
    }

    const scrollOnce = () => alignMessageToTop(messageElement, container)
    let secondFrame: number | null = null
    const firstFrame = requestAnimationFrame(() => {
      scrollOnce()
      secondFrame = requestAnimationFrame(scrollOnce)
    })

    prevUserMessageCountRef.current = userMessageCount

    return () => {
      cancelAnimationFrame(firstFrame)
      if (secondFrame !== null) {
        cancelAnimationFrame(secondFrame)
      }
    }
  }, [latestUserMessageIndex, isNewUserMessage, scrollContainerRef, userMessageCount])

  if (messages.length === 0) {
    return (
      <div className="empty-state">
        <p>Start a conversation by sending a message!</p>
      </div>
    )
  }

  return (
    <div className="messages-container" ref={messagesContainerRef}>
      {messages.map((message, index) => {
        const isLatestUserMessage = message.role === 'user' && index === latestUserMessageIndex
        
        return (
          <div
            key={index}
            ref={isLatestUserMessage ? latestUserMessageRef : null}
            className={`message-wrapper ${message.role}`}
          >
            <div className="message-bubble">
              <div className="message-content">{message.content}</div>
            </div>
          </div>
        )
      })}
      {loading && (
        <div className="message-wrapper assistant">
          <div className="message-bubble">
            <div className="typing-indicator">
              <span></span>
              <span></span>
              <span></span>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

