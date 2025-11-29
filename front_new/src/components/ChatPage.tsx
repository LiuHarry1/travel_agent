import { useState, useRef } from 'react'
import { MessageList } from './MessageList'

interface Message {
  role: 'user' | 'assistant'
  content: string
}

export default function ChatPage() {
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const messagesWrapperRef = useRef<HTMLDivElement>(null)

  // Mock agent response generator
  const generateMockResponse = async (userMessage: string): Promise<string> => {
    // Simulate network delay
    await new Promise(resolve => setTimeout(resolve, 500))
    
    // Generate a longer response to demonstrate scrolling
    const responses = [
      `I understand you said: "${userMessage}". Let me provide you with a detailed response. This is a longer message to demonstrate how the user's message gets pushed up naturally when the agent response is long. The scroll behavior should feel natural and smooth, just like in a real chat application.`,
      `That's an interesting question! Here's a comprehensive answer that will help you understand better. This response is intentionally longer to show how the scrolling works when agent messages are lengthy. Notice how your message stays visible at first, then gets pushed up as more content arrives.`,
      `Great point! Let me elaborate on that. This is a multi-sentence response designed to test the scroll behavior. As this message grows, you should see your user message gradually move up the screen, which is the expected behavior.`
    ]
    
    // Return a response based on message length or random
    const index = userMessage.length % responses.length
    return responses[index]
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    
    if (!input.trim() || loading) return

    const userMessage = input.trim()
    setInput('')
    
    // Add user message immediately
    const newUserMessage: Message = {
      role: 'user',
      content: userMessage
    }
    
    setMessages(prev => [...prev, newUserMessage])
    setLoading(true)

    // Generate and add assistant response
    try {
      const response = await generateMockResponse(userMessage)
      
      // Simulate streaming by adding content gradually
      const words = response.split(' ')
      let accumulatedContent = ''
      
      for (let i = 0; i < words.length; i++) {
        accumulatedContent += (i > 0 ? ' ' : '') + words[i]
        
        setMessages(prev => {
          const updated = [...prev]
          const lastMessage = updated[updated.length - 1]
          
          if (lastMessage && lastMessage.role === 'assistant') {
            updated[updated.length - 1] = {
              ...lastMessage,
              content: accumulatedContent
            }
          } else {
            updated.push({
              role: 'assistant',
              content: accumulatedContent
            })
          }
          
          return updated
        })
        
        // Small delay between words to simulate streaming
        await new Promise(resolve => setTimeout(resolve, 50))
      }
    } catch (error) {
      console.error('Error generating response:', error)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="chat-page">
      <div className="chat-header">
        <h1>Chatbot - Scroll to Top Demo</h1>
        <p>Send a message to see it scroll to the top!</p>
      </div>
      
      <div className="chat-messages-wrapper" ref={messagesWrapperRef}>
        <MessageList messages={messages} loading={loading} scrollContainerRef={messagesWrapperRef} />
      </div>
      
      <div className="chat-input-container">
        <form onSubmit={handleSubmit} className="chat-form">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Type your message..."
            className="chat-input"
            disabled={loading}
          />
          <button 
            type="submit" 
            className="send-button"
            disabled={loading || !input.trim()}
          >
            {loading ? 'Sending...' : 'Send'}
          </button>
        </form>
      </div>
    </div>
  )
}

