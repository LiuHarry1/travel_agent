import { useState, useCallback } from 'react'

interface CopyToClipboardResult {
  /** Whether the text was successfully copied */
  copied: boolean
  /** Function to copy text to clipboard */
  copy: (text: string) => Promise<void>
  /** Reset the copied state */
  reset: () => void
}

/**
 * Custom hook for copying text to clipboard with feedback
 * 
 * @param timeout - Time in milliseconds before resetting the copied state (default: 2000)
 * @returns Object with copied state, copy function, and reset function
 * 
 * @example
 * ```tsx
 * const { copied, copy } = useCopyToClipboard();
 * 
 * return (
 *   <button onClick={() => copy('Hello World')}>
 *     {copied ? 'Copied!' : 'Copy'}
 *   </button>
 * );
 * ```
 */
export function useCopyToClipboard(timeout = 2000): CopyToClipboardResult {
  const [copied, setCopied] = useState(false)

  const copy = useCallback(
    async (text: string) => {
      if (!navigator?.clipboard) {
        console.warn('Clipboard not supported')
        return
      }

      try {
        await navigator.clipboard.writeText(text)
        setCopied(true)
        
        // Auto-reset after timeout
        setTimeout(() => {
          setCopied(false)
        }, timeout)
      } catch (error) {
        console.error('Failed to copy to clipboard:', error)
        setCopied(false)
      }
    },
    [timeout]
  )

  const reset = useCallback(() => {
    setCopied(false)
  }, [])

  return { copied, copy, reset }
}

