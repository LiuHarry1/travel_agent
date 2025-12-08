import { memo } from 'react'
import type { ValidationResult } from '../../api/config'
import './ValidationDisplay.css'

interface ValidationDisplayProps {
  validationResult: ValidationResult | null
}

function ValidationDisplay({ validationResult }: ValidationDisplayProps) {
  if (!validationResult) {
    return null
  }

  return (
    <div className={`validation-result ${validationResult.valid ? 'valid' : 'invalid'}`}>
      <strong>Validation:</strong>{' '}
      {validationResult.valid ? (
        <span className="valid-text">✓ Configuration is valid</span>
      ) : (
        <div className="invalid-text">
          <span>✗ Configuration has errors:</span>
          <pre>{JSON.stringify(validationResult.errors, null, 2)}</pre>
        </div>
      )}
    </div>
  )
}

export default memo(ValidationDisplay)

