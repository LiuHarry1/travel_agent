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

/**
 * 将配置对象转换为 YAML 字符串
 * @param config - 配置对象
 * @returns YAML 字符串
 */
export function stringifyYaml(config: ParsedPipelineConfig): string {
  try {
    return yaml.dump(config, {
      indent: 2,
      lineWidth: -1,
      noRefs: true,
    })
  } catch (error) {
    if (error instanceof Error) {
      throw new Error(`Failed to stringify YAML: ${error.message}`)
    }
    throw new Error('Failed to stringify YAML: Unknown error')
  }
}

