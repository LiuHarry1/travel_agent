/**
 * Markdown utility functions
 */

import { IMAGE_URL_PATTERN, DEFAULT_IMAGE_ALT_TEXT } from '../constants'

/**
 * Convert image URLs in text to Markdown image format.
 * Detects URLs ending with image extensions and converts them to ![alt](url) format.
 * 
 * @param content - The text content that may contain image URLs
 * @returns The content with image URLs converted to Markdown format
 */
export function convertImageUrlsToMarkdown(content: string): string {
  return content.replace(IMAGE_URL_PATTERN, (match) => {
    // Check if this URL is already part of a Markdown image
    // If it's already in ![alt](url) format, don't convert it
    const beforeMatch = content.substring(0, content.indexOf(match))
    const afterMatch = content.substring(content.indexOf(match) + match.length)
    
    // If there's a ! before and ( after, it's already a Markdown image
    if (beforeMatch.endsWith('![') && afterMatch.startsWith('](')) {
      return match
    }
    
    // Convert to Markdown image format
    // Extract filename for alt text
    const filename = match.split('/').pop()?.split('.')[0] || DEFAULT_IMAGE_ALT_TEXT
    return `![${filename}](${match})`
  })
}
