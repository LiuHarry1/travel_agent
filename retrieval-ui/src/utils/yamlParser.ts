import * as yaml from 'js-yaml'
import type { ParsedPipelineConfig } from '../api/config'

/**
 * 解析 YAML 字符串为配置对象
 * @param yamlString - YAML 字符串
 * @returns 解析后的配置对象
 * @throws 如果 YAML 格式无效
 */
export function parseYaml(yamlString: string): ParsedPipelineConfig {
  try {
    const parsed = yaml.load(yamlString) as ParsedPipelineConfig
    return parsed || {}
  } catch (error) {
    if (error instanceof Error) {
      throw new Error(`Failed to parse YAML: ${error.message}`)
    }
    throw new Error('Failed to parse YAML: Unknown error')
  }
}



