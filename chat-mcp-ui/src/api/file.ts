/**
 * File upload API endpoints
 */

import { getApiUrl } from './client'

export interface FileUploadResponse {
  filename: string
  content: string
  size: number
}

export async function uploadFile(
  file: File,
  onProgress?: (progress: number) => void
): Promise<FileUploadResponse> {
  const formData = new FormData()
  formData.append('file', file)

  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest()

    // Track upload progress
    xhr.upload.addEventListener('progress', (e) => {
      if (e.lengthComputable && onProgress) {
        const progress = Math.round((e.loaded / e.total) * 100)
        onProgress(progress)
      }
    })

    // Handle completion
    xhr.addEventListener('load', () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        try {
          const response = JSON.parse(xhr.responseText) as FileUploadResponse
          resolve(response)
        } catch (e) {
          reject(new Error('Failed to parse response'))
        }
      } else {
        const detail = xhr.responseText || `Upload failed with status ${xhr.status}`
        reject(new Error(detail))
      }
    })

    // Handle errors
    xhr.addEventListener('error', () => {
      reject(new Error('Network error occurred'))
    })

    xhr.addEventListener('abort', () => {
      reject(new Error('Upload was aborted'))
    })

    // Start the request
    xhr.open('POST', getApiUrl('/upload/file'))
    xhr.send(formData)
  })
}

