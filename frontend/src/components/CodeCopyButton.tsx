import { useCopyToClipboard } from '../hooks/useCopyToClipboard'

interface CodeCopyButtonProps {
  code: string
  className?: string
}

/**
 * Reusable code copy button component with visual feedback
 */
export function CodeCopyButton({ code, className = '' }: CodeCopyButtonProps) {
  const { copied, copy } = useCopyToClipboard(2000)

  return (
    <button
      className={`code-copy-button ${className}`}
      onClick={() => copy(code)}
      title={copied ? 'Copied!' : 'Copy code'}
      type="button"
    >
      {copied ? (
        <>
          <svg
            width="16"
            height="16"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <polyline points="20 6 9 17 4 12" />
          </svg>
          <span className="code-copy-text">Copied!</span>
        </>
      ) : (
        <>
          <svg
            width="16"
            height="16"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <rect x="9" y="9" width="13" height="13" rx="2" ry="2" />
            <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1" />
          </svg>
          <span className="code-copy-text">Copy code</span>
        </>
      )}
    </button>
  )
}

