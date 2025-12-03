import React from 'react';
import { ProcessingError } from '../types/processing';
import './ErrorDisplay.css';

interface ErrorDisplayProps {
  error: ProcessingError;
  onRetry?: () => void;
  onDismiss?: () => void;
}

export const ErrorDisplay: React.FC<ErrorDisplayProps> = ({
  error,
  onRetry,
  onDismiss,
}) => {
  const isCritical = error.errorType === 'NoChunksError' || !error.retryable;
  const errorClass = isCritical ? 'error-critical' : '';

  return (
    <div className={`error-display ${errorClass}`}>
      <div className="error-header">
        <div>
          <h3>处理失败!</h3>
          <span className="error-icon">❌</span>
        </div>
        {onDismiss && (
          <button className="dismiss-btn" onClick={onDismiss} aria-label="关闭">
            ×
          </button>
        )}
      </div>
      
      <p className="error-message-text">{error.error}</p>
      
      {error.errorType && (
        <div className="error-type">
          <strong>错误类型:</strong> <code>{error.errorType}</code>
        </div>
      )}
      
      {error.retryCount > 0 && (
        <div className="retry-info">
          已重试 {error.retryCount} 次
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
              重试 ({error.retryCount + 1}/3)
            </button>
          ) : (
            <p className="no-retry-message">已达到最大重试次数。</p>
          )}
        </div>
      )}
      
      {!error.retryable && (
        <div className="error-note">
          <p>⚠️ 此错误无法自动重试，请检查配置或联系管理员</p>
        </div>
      )}
    </div>
  );
};
