/**
 * Hook for managing file upload state with content tracking
 */

import { useState, useEffect } from 'react'
import { uploadFile } from '../api/index'
import type { Alert } from '../types'

interface FileWithContent {
  file: File
  content?: string
  loading?: boolean
  error?: string
  progress?: number
}

export function useFileUploadState(
  uploadedFiles: File[],
  setAlert: (alert: Alert | null) => void
) {
  const [filesWithContent, setFilesWithContent] = useState<FileWithContent[]>([])

  // Upload files to backend immediately when they're added
  useEffect(() => {
    const uploadFiles = async () => {
      const newFiles = uploadedFiles.filter(
        (file) => !filesWithContent.find((fwc) => fwc.file === file)
      )

      if (newFiles.length === 0) return

      // Immediately add new files with loading state
      setFilesWithContent((prev) => {
        const newFilesWithContent = newFiles.map((file) => ({ 
          file, 
          loading: true, 
          progress: 0 
        }))
        return [...prev, ...newFilesWithContent]
      })

      // Upload each new file immediately
      for (const file of newFiles) {
        try {
          const result = await uploadFile(
            file,
            (progress) => {
              // Update progress in real-time
              setFilesWithContent((prev) =>
                prev.map((fwc) =>
                  fwc.file === file ? { ...fwc, progress } : fwc
                )
              )
            }
          )
          setFilesWithContent((prev) =>
            prev.map((fwc) =>
              fwc.file === file 
                ? { file, content: result.content, loading: false, progress: 100 } 
                : fwc
            )
          )
        } catch (error) {
          const errorMessage = error instanceof Error ? error.message : 'Upload failed'
          setFilesWithContent((prev) =>
            prev.map((fwc) =>
              fwc.file === file 
                ? { file, loading: false, error: errorMessage, progress: 0 } 
                : fwc
            )
          )
          setAlert({ type: 'error', message: `Failed to upload ${file.name}: ${errorMessage}` })
        }
      }
    }

    uploadFiles()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [uploadedFiles, setAlert])

  // Sync with uploadedFiles (remove if removed from uploadedFiles)
  useEffect(() => {
    setFilesWithContent((prev) => prev.filter((fwc) => uploadedFiles.includes(fwc.file)))
  }, [uploadedFiles])

  const clearFiles = () => {
    setFilesWithContent([])
  }

  return {
    filesWithContent,
    clearFiles,
  }
}

