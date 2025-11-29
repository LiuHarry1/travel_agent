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

// Helper function to perform the actual scroll
// Direct calculation method - more reliable than scrollIntoView for container scrolling
const performScroll = (messageElement: HTMLElement, container: HTMLElement, messageIndex: number, retryCount = 0) => {
  // Force layout recalculation
  void container.offsetHeight
  void messageElement.offsetHeight
  
  // Wait for layout to settle
  requestAnimationFrame(() => {
    requestAnimationFrame(() => {
      // Get container dimensions first
      const scrollHeight = container.scrollHeight
      const clientHeight = container.clientHeight
      const canScroll = scrollHeight > clientHeight
      
      // If container cannot scroll yet and we haven't retried too many times, wait and retry
      if (!canScroll && retryCount < 3) {
        setTimeout(() => {
          performScroll(messageElement, container, messageIndex, retryCount + 1)
        }, 50)
        return
      }
      
      // Get positions
      const messageRect = messageElement.getBoundingClientRect()
      const containerRect = container.getBoundingClientRect()
      
      // Calculate message's position relative to container's visible top
      const messageTopRelativeToContainer = messageRect.top - containerRect.top
      
      // Calculate absolute position in scroll space
      const currentScrollTop = container.scrollTop
      const messageAbsoluteScrollPosition = currentScrollTop + messageTopRelativeToContainer
      
      // Account for container padding (20px from CSS)
      const containerPadding = 20
      const targetScrollTop = Math.max(0, messageAbsoluteScrollPosition - containerPadding)
      
      // Get max scroll position
      const maxScrollTop = Math.max(0, scrollHeight - clientHeight)
      
      // If target is greater than max, it means content is still growing
      // In that case, use target anyway (browser will clamp it)
      // But if maxScrollTop is 0 and target > 0, we need to wait
      const validTargetScrollTop = maxScrollTop > 0 
        ? Math.min(targetScrollTop, maxScrollTop)
        : (canScroll ? targetScrollTop : 0)
      
      // Set scroll position using multiple methods for reliability
      if (canScroll || validTargetScrollTop > 0) {
        container.scrollTop = validTargetScrollTop
        container.scrollTo({
          top: validTargetScrollTop,
          behavior: 'auto'
        })
        
        // Force reflow
        void container.offsetHeight
        
        // Set again in next frame to ensure it sticks
        requestAnimationFrame(() => {
          container.scrollTop = validTargetScrollTop
          void container.offsetHeight
        })
      }
      
      // Verify after a short delay
      setTimeout(() => {
        const actualScrollTop = container.scrollTop
        const finalScrollHeight = container.scrollHeight
        const finalClientHeight = container.clientHeight
        const finalCanScroll = finalScrollHeight > finalClientHeight
        
        // Recalculate if container grew
        if (finalCanScroll && !canScroll) {
          // Container can now scroll, recalculate
          const finalMessageRect = messageElement.getBoundingClientRect()
          const finalContainerRect = container.getBoundingClientRect()
          const finalTop = finalMessageRect.top - finalContainerRect.top
          const finalAbsolute = actualScrollTop + finalTop
          const finalTarget = Math.max(0, finalAbsolute - containerPadding)
          const finalMax = finalScrollHeight - finalClientHeight
          const finalValid = Math.min(finalTarget, finalMax)
          
          container.scrollTop = finalValid
          container.scrollTo({ top: finalValid, behavior: 'auto' })
          void container.offsetHeight
          
          setTimeout(() => {
            const verifyTop = messageElement.getBoundingClientRect().top - container.getBoundingClientRect().top
            const verifyAdjustment = verifyTop - containerPadding
            console.log('Scrolled to top (delayed recalculation):', {
              messageIndex,
              finalValid,
              verifyTop,
              verifyAdjustment,
              scrollSuccess: Math.abs(verifyAdjustment) < 5,
              finalScrollHeight,
              finalClientHeight
            })
          }, 10)
          return
        }
        
        const finalMessageRect = messageElement.getBoundingClientRect()
        const finalContainerRect = container.getBoundingClientRect()
        const finalTop = finalMessageRect.top - finalContainerRect.top
        const finalAdjustment = finalTop - containerPadding
        
        const scrollSuccess = Math.abs(finalAdjustment) < 5
        
        console.log('Scrolled to top (direct calculation):', {
          messageIndex,
          targetScrollTop,
          validTargetScrollTop,
          actualScrollTop,
          messageAbsoluteScrollPosition,
          messageTopRelativeToContainer,
          finalTop,
          finalAdjustment,
          scrollSuccess,
          scrollHeight: finalScrollHeight,
          clientHeight: finalClientHeight,
          maxScrollTop: finalScrollHeight - finalClientHeight,
          canScroll: finalCanScroll,
          retryCount
        })
        
        // If not successful and container can scroll, try again
        if (!scrollSuccess && finalCanScroll) {
          // Recalculate with current positions
          const retryMessageRect = messageElement.getBoundingClientRect()
          const retryContainerRect = container.getBoundingClientRect()
          const retryTop = retryMessageRect.top - retryContainerRect.top
          const retryAbsolute = actualScrollTop + retryTop
          const retryTarget = Math.max(0, retryAbsolute - containerPadding)
          const retryMax = finalScrollHeight - finalClientHeight
          const retryValid = Math.min(retryTarget, retryMax)
          
          container.scrollTop = retryValid
          container.scrollTo({ top: retryValid, behavior: 'auto' })
          void container.offsetHeight
          
          setTimeout(() => {
            const retryFinalTop = messageElement.getBoundingClientRect().top - container.getBoundingClientRect().top
            const retryFinalAdjustment = retryFinalTop - containerPadding
            console.log('Retry scroll result:', {
              retryValid,
              retryFinalTop,
              retryFinalAdjustment,
              success: Math.abs(retryFinalAdjustment) < 5
            })
          }, 10)
        }
      }, 30)
    })
  })
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
    // Only scroll if we have a new user message
    if (isNewUserMessage && latestUserMessageIndex >= 0 && latestUserMessageRef.current && scrollContainerRef?.current) {
      const container = scrollContainerRef.current
      const messageElement = latestUserMessageRef.current
      
      // Use multiple requestAnimationFrame to ensure DOM is fully rendered and layout is complete
      requestAnimationFrame(() => {
        requestAnimationFrame(() => {
          requestAnimationFrame(() => {
            if (!messageElement || !container) return
            
            // Wait longer to ensure container is ready and content is fully rendered
            // Use a longer delay to allow React to finish rendering and browser to calculate layout
            setTimeout(() => {
              if (!messageElement || !container) return
              
              // Check if container is ready to scroll
              const scrollHeight = container.scrollHeight
              const clientHeight = container.clientHeight
              const canScroll = scrollHeight > clientHeight
              
              if (!canScroll) {
                // Container not ready yet, retry with longer delay
                // This happens when content is still being rendered
                setTimeout(() => {
                  if (!messageElement || !container) return
                  
                  // Check again
                  const retryScrollHeight = container.scrollHeight
                  const retryClientHeight = container.clientHeight
                  const retryCanScroll = retryScrollHeight > retryClientHeight
                  
                  if (retryCanScroll) {
                    performScroll(messageElement, container, latestUserMessageIndex)
                  } else {
                    // Still can't scroll, but try anyway (content might be exactly fitting)
                    // Force a layout recalculation by accessing offsetHeight
                    const _ = container.offsetHeight
                    performScroll(messageElement, container, latestUserMessageIndex)
                  }
                }, 100) // Longer delay for content to render
                return
              }
              
              performScroll(messageElement, container, latestUserMessageIndex)
            }, 50) // Initial delay increased
          })
        })
      })
    }
    
    // Update the ref for next comparison
    prevUserMessageCountRef.current = userMessageCount
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

