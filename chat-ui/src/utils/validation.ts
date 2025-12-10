/**
 * Validation utility functions
 */

import { MAX_FILE_SIZE, VALID_FILE_EXTENSIONS } from '../constants'

export interface FileValidationResult {
  valid: boolean
  error?: {
    type: 'size' | 'format'
    message: string
  }
}

/**
 * Validate file size and format
 * 
 * @param file - File to validate
 * @returns Validation result
 */
export function validateFile(file: File): FileValidationResult {
  // Check file size
  if (file.size > MAX_FILE_SIZE) {
    return {
      valid: false,
      error: {
        type: 'size',
        message: `File size exceeds ${MAX_FILE_SIZE / (1024 * 1024)}MB limit`,
      },
    }
  }
  
  // Check file extension
  const fileExtension = file.name.toLowerCase().slice(file.name.lastIndexOf('.'))
  const isValidType = 
    VALID_FILE_EXTENSIONS.includes(fileExtension) || 
    file.type.startsWith('text/') ||
    file.type === 'application/pdf' ||
    file.type === 'application/msword' ||
    file.type === 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
  
  if (!isValidType) {
    return {
      valid: false,
      error: {
        type: 'format',
        message: `Unsupported file format. Allowed: ${VALID_FILE_EXTENSIONS.join(', ')}`,
      },
    }
  }
  
  return { valid: true }
}

/**
 * Validate multiple files
 * 
 * @param files - Array of files to validate
 * @returns Array of validation results
 */
export function validateFiles(files: File[]): FileValidationResult[] {
  return files.map(validateFile)
}

/**
 * Check if a string is a valid URL
 * 
 * @param url - String to check
 * @returns True if valid URL
 */
export function isValidUrl(url: string): boolean {
  try {
    new URL(url)
    return true
  } catch {
    return false
  }
}

/**
 * Check if a string is not empty after trimming
 * 
 * @param value - String to check
 * @returns True if not empty
 */
export function isNotEmpty(value: string): boolean {
  return value.trim().length > 0
}
