import React, { useState } from 'react';
import { X, AlertTriangle, XCircle, Copy, Check } from 'lucide-react';
import { ProcessingError } from '../types/processing';
import './ErrorDisplay.css';

interface ErrorDisplayProps {
  error: ProcessingError;
  onRetry?: () => void;
  onDismiss?: () => void;
}

const getErrorSolution = (errorType?: string, errorMessage?: string): string | null => {
  if (!errorType) return null;
  
  const message = errorMessage?.toLowerCase() || '';
  
  if (errorType === 'NoChunksError' || message.includes('no chunks')) {
    return 'The document may be empty or in an unsupported format. Try uploading a different file.';
  }
  
  if (message.includes('connection') || message.includes('network') || message.includes('timeout')) {
    return 'Check your internet connection and API endpoint settings. The service may be temporarily unavailable.';
  }
  
  if (message.includes('api key') || message.includes('authentication') || message.includes('unauthorized')) {
    return 'Verify your API key in the settings. Make sure it has the correct permissions.';
  }
  
  if (message.includes('quota') || message.includes('limit') || message.includes('rate limit')) {
    return 'You may have exceeded your API quota or rate limit. Wait a moment and try again, or check your usage limits.';
  }
  
  if (message.includes('embedding') || message.includes('dimension')) {
    return 'There may be a mismatch in embedding dimensions. Check your embedding configuration in settings.';
  }
  
  if (message.includes('collection') || message.includes('database')) {
    return 'The collection or database may not exist. Try refreshing or creating a new collection.';
  }
  
  if (message.includes('file size') || message.includes('too large')) {
    return 'The file may be too large. Try splitting it into smaller files or check the maximum file size limit.';
  }
  
  return 'Please check your configuration and try again. If the problem persists, contact support.';
};

export const ErrorDisplay: React.FC<ErrorDisplayProps> = ({
  error,
  onRetry,
  onDismiss,
}) => {
  const [copied, setCopied] = useState(false);
  const isCritical = error.errorType === 'NoChunksError' || !error.retryable;
  const errorClass = isCritical ? 'error-critical' : '';
  const solution = getErrorSolution(error.errorType, error.error);

  const copyError = async () => {
    const errorText = `Error Type: ${error.errorType || 'Unknown'}\nError: ${error.error}\nRetry Count: ${error.retryCount}`;
    try {
      await navigator.clipboard.writeText(errorText);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error('Failed to copy error:', err);
    }
  };

  return (
    <div className={`error-display ${errorClass}`}>
      <div className="error-header">
        <div>
          <h3>Processing Failed!</h3>
          <XCircle size={20} className="error-icon" />
        </div>
        {onDismiss && (
          <button className="dismiss-btn" onClick={onDismiss} aria-label="Close">
            <X size={20} />
          </button>
        )}
      </div>
      
      <div className="error-message-section">
        <p className="error-message-text">{error.error}</p>
        <button
          className="copy-error-btn"
          onClick={copyError}
          title="Copy error details"
          aria-label="Copy error details"
        >
          {copied ? <Check size={16} /> : <Copy size={16} />}
          {copied ? 'Copied!' : 'Copy'}
        </button>
      </div>
      
      {solution && (
        <div className="error-solution">
          <strong>💡 Suggested Solution:</strong>
          <p>{solution}</p>
        </div>
      )}
      
      {error.errorType && (
        <div className="error-type">
          <strong>Error Type:</strong> <code>{error.errorType}</code>
        </div>
      )}
      
      {error.retryCount > 0 && (
        <div className="retry-info">
          Retried {error.retryCount} time(s)
        </div>
      )}
      
      {error.retryable && (
        <div className="error-actions">
          {error.retryCount < 3 ? (
            <button
              className="retry-btn"
              onClick={onRetry}
              disabled={error.retryCount >= 3}
            >
              Retry ({error.retryCount + 1}/3)
            </button>
          ) : (
            <p className="no-retry-message">Maximum retry attempts reached.</p>
          )}
        </div>
      )}
      
      {!error.retryable && (
        <div className="error-note">
          <p>
            <AlertTriangle size={16} style={{ display: 'inline', verticalAlign: 'middle', marginRight: '8px' }} />
            This error cannot be automatically retried. Please check your configuration or contact an administrator.
          </p>
        </div>
      )}
    </div>
  );
};
