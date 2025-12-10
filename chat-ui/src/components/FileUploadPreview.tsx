/**
 * File upload preview component
 * Displays uploaded files with progress and error states
 */

import { memo } from 'react'
import { FileIcon, ErrorIcon, CloseIcon } from './icons'

export interface FileWithContent {
  file: File
  content?: string
  loading?: boolean
  error?: string
  progress?: number
}

interface FileUploadPreviewProps {
  files: FileWithContent[]
  uploadedFiles: File[]
  onRemoveFile: (index: number) => void
}

export const FileUploadPreview = memo(function FileUploadPreview({ files, uploadedFiles, onRemoveFile }: FileUploadPreviewProps) {
  if (files.length === 0) {
    return null
  }

  return (
    <div className="files-preview-inside">
      {files.map((fwc, index) => (
        <div
          key={index}
          className={`file-preview-chip ${fwc.error ? 'error' : ''} ${fwc.loading ? 'loading' : ''}`}
        >
          <div className="file-chip-icon">
            {fwc.loading ? (
              <div className="loading-spinner small"></div>
            ) : fwc.error ? (
              <ErrorIcon />
            ) : (
              <FileIcon />
            )}
          </div>
          <span className="file-chip-name">{fwc.file.name}</span>
          {fwc.error && <span className="file-chip-error">✗</span>}
          {fwc.loading && fwc.progress !== undefined && (
            <div className="file-chip-progress">
              <div className="file-chip-progress-bar">
                <div
                  className="file-chip-progress-fill"
                  style={{ width: `${fwc.progress}%` }}
                ></div>
              </div>
              <span className="file-chip-progress-text">{fwc.progress}%</span>
            </div>
          )}
          <button
            type="button"
            onClick={() => {
              const fileIndex = uploadedFiles.indexOf(fwc.file)
              if (fileIndex !== -1) onRemoveFile(fileIndex)
            }}
            className="file-chip-remove"
            title="Remove file"
          >
            <CloseIcon />
          </button>
        </div>
      ))}
    </div>
  )
})
