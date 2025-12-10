/**
 * Error Boundary Component
 * Catches React component errors and displays a fallback UI
 */

import { Component, type ReactNode, type ErrorInfo } from 'react'

interface ErrorBoundaryProps {
  children: ReactNode
  fallback?: ReactNode
  onError?: (error: Error, errorInfo: ErrorInfo) => void
}

interface ErrorBoundaryState {
  hasError: boolean
  error: Error | null
}

export class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  constructor(props: ErrorBoundaryProps) {
    super(props)
    this.state = {
      hasError: false,
      error: null,
    }
  }

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return {
      hasError: true,
      error,
    }
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    // Log error for debugging
    console.error('ErrorBoundary caught an error:', error, errorInfo)
    
    // Call optional error handler
    if (this.props.onError) {
      this.props.onError(error, errorInfo)
    }

    // TODO: Send error to error reporting service (e.g., Sentry)
    // errorReportingService.captureException(error, { extra: errorInfo })
  }

  handleReset = () => {
    this.setState({
      hasError: false,
      error: null,
    })
  }

  render() {
    if (this.state.hasError) {
      if (this.props.fallback) {
        return this.props.fallback
      }

      return (
        <div className="error-boundary">
          <div className="error-boundary-content">
            <h2>Something went wrong</h2>
            <p>
              {this.state.error?.message || 'An unexpected error occurred'}
            </p>
            <button
              type="button"
              onClick={this.handleReset}
              className="error-boundary-reset-btn"
            >
              Try again
            </button>
            <details className="error-boundary-details">
              <summary>Error details</summary>
              <pre className="error-boundary-stack">
                {this.state.error?.stack}
              </pre>
            </details>
          </div>
        </div>
      )
    }

    return this.props.children
  }
}
