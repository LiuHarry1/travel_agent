import { ChunkLocation } from '../api/client';

/**
 * Generate readable text for location information
 */
export function getLocationDisplayText(location?: ChunkLocation): string {
  if (!location) return '';
  
  const parts: string[] = [];
  
  if (location.page_number !== undefined) {
    parts.push(`Page ${location.page_number}`);
  }
  
  if (location.heading_path && location.heading_path.length > 0) {
    parts.push(`Section: ${location.heading_path.join(' > ')}`);
  }
  
  if (location.paragraph_index !== undefined) {
    parts.push(`Paragraph ${location.paragraph_index + 1}`);
  }
  
  if (location.section_index !== undefined) {
    parts.push(`Section ${location.section_index + 1}`);
  }
  
  if (location.code_block_index !== undefined) {
    parts.push(`Code Block ${location.code_block_index + 1}`);
  }
  
  if (location.image_index !== undefined) {
    parts.push(`Image ${location.image_index + 1}`);
  }
  
  if (location.table_index !== undefined) {
    parts.push(`Table ${location.table_index + 1}`);
    if (location.table_cell) {
      parts.push(`Cell ${location.table_cell}`);
    }
  }
  
  return parts.join(', ');
}

/**
 * Get location information badge array
 */
export function getLocationBadges(location?: ChunkLocation): Array<{ label: string; value: string; type: string }> {
  if (!location) return [];
  
  const badges: Array<{ label: string; value: string; type: string }> = [];
  
  if (location.page_number !== undefined) {
    badges.push({ label: 'Page', value: String(location.page_number), type: 'page' });
  }
  
  if (location.heading_path && location.heading_path.length > 0) {
    badges.push({ label: 'Section', value: location.heading_path.join(' > '), type: 'heading' });
  }
  
  if (location.paragraph_index !== undefined) {
    badges.push({ label: 'Paragraph', value: String(location.paragraph_index + 1), type: 'paragraph' });
  }
  
  if (location.section_index !== undefined) {
    badges.push({ label: 'Section Index', value: String(location.section_index + 1), type: 'section' });
  }
  
  if (location.code_block_index !== undefined) {
    badges.push({ label: 'Code Block', value: String(location.code_block_index + 1), type: 'code' });
  }
  
  if (location.image_index !== undefined) {
    badges.push({ label: 'Image', value: String(location.image_index + 1), type: 'image' });
  }
  
  if (location.table_index !== undefined) {
    badges.push({ label: 'Table', value: String(location.table_index + 1), type: 'table' });
  }
  
  return badges;
}

/**
 * Filter empty metadata values
 */
export function filterEmptyMetadata(metadata?: Record<string, any>): Record<string, any> {
  if (!metadata) return {};
  
  const filtered: Record<string, any> = {};
  for (const [key, value] of Object.entries(metadata)) {
    if (value !== null && value !== undefined && value !== '') {
      // Exclude location as it has a dedicated display area
      if (key !== 'location') {
        filtered[key] = value;
      }
    }
  }
  return filtered;
}

/**
 * Format JSON metadata display
 */
export function formatMetadata(metadata?: Record<string, any>): string {
  if (!metadata || Object.keys(metadata).length === 0) {
    return '{}';
  }
  
  try {
    return JSON.stringify(metadata, null, 2);
  } catch (e) {
    return String(metadata);
  }
}

