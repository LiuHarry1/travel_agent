import { ChunkLocation } from '../api/client';

/**
 * 生成位置信息的可读文本
 */
export function getLocationDisplayText(location?: ChunkLocation): string {
  if (!location) return '';
  
  const parts: string[] = [];
  
  if (location.page_number !== undefined) {
    parts.push(`第 ${location.page_number} 页`);
  }
  
  if (location.heading_path && location.heading_path.length > 0) {
    parts.push(`章节: ${location.heading_path.join(' > ')}`);
  }
  
  if (location.paragraph_index !== undefined) {
    parts.push(`段落 ${location.paragraph_index + 1}`);
  }
  
  if (location.section_index !== undefined) {
    parts.push(`章节 ${location.section_index + 1}`);
  }
  
  if (location.code_block_index !== undefined) {
    parts.push(`代码块 ${location.code_block_index + 1}`);
  }
  
  if (location.image_index !== undefined) {
    parts.push(`图片 ${location.image_index + 1}`);
  }
  
  if (location.table_index !== undefined) {
    parts.push(`表格 ${location.table_index + 1}`);
    if (location.table_cell) {
      parts.push(`单元格 ${location.table_cell}`);
    }
  }
  
  return parts.join(', ');
}

/**
 * 获取位置信息标签数组
 */
export function getLocationBadges(location?: ChunkLocation): Array<{ label: string; value: string; type: string }> {
  if (!location) return [];
  
  const badges: Array<{ label: string; value: string; type: string }> = [];
  
  if (location.page_number !== undefined) {
    badges.push({ label: '页码', value: String(location.page_number), type: 'page' });
  }
  
  if (location.heading_path && location.heading_path.length > 0) {
    badges.push({ label: '章节', value: location.heading_path.join(' > '), type: 'heading' });
  }
  
  if (location.paragraph_index !== undefined) {
    badges.push({ label: '段落', value: String(location.paragraph_index + 1), type: 'paragraph' });
  }
  
  if (location.section_index !== undefined) {
    badges.push({ label: '章节索引', value: String(location.section_index + 1), type: 'section' });
  }
  
  if (location.code_block_index !== undefined) {
    badges.push({ label: '代码块', value: String(location.code_block_index + 1), type: 'code' });
  }
  
  if (location.image_index !== undefined) {
    badges.push({ label: '图片', value: String(location.image_index + 1), type: 'image' });
  }
  
  if (location.table_index !== undefined) {
    badges.push({ label: '表格', value: String(location.table_index + 1), type: 'table' });
  }
  
  return badges;
}

/**
 * 过滤空值元数据
 */
export function filterEmptyMetadata(metadata?: Record<string, any>): Record<string, any> {
  if (!metadata) return {};
  
  const filtered: Record<string, any> = {};
  for (const [key, value] of Object.entries(metadata)) {
    if (value !== null && value !== undefined && value !== '') {
      // 排除 location，因为它有专门的展示区域
      if (key !== 'location') {
        filtered[key] = value;
      }
    }
  }
  return filtered;
}

/**
 * 格式化 JSON 元数据展示
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

