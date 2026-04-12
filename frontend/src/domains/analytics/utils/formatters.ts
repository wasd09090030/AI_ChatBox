/**
 * 文件说明：前端业务域逻辑与接口封装。
 */

import type { AnalyticsDistributionItem } from '@/domains/analytics/types'

/** 功能：函数 formatCompactNumber，负责 formatCompactNumber 相关处理。 */
export function formatCompactNumber(value?: number | null): string {
  if (value == null) return '0'
  return new Intl.NumberFormat('zh-CN', {
    notation: value >= 1000 ? 'compact' : 'standard',
    maximumFractionDigits: value >= 1000 ? 1 : 0,
  }).format(value)
}

/** 功能：函数 formatPercent，负责 formatPercent 相关处理。 */
export function formatPercent(value?: number | null): string {
  if (value == null) return '0.0%'
  return `${(value * 100).toFixed(1)}%`
}

/** 功能：函数 formatSeconds，负责 formatSeconds 相关处理。 */
export function formatSeconds(value?: number | null): string {
  if (value == null) return '0.00s'
  return `${value.toFixed(2)}s`
}

/** 功能：函数 formatTimestamp，负责 formatTimestamp 相关处理。 */
export function formatTimestamp(timestamp: string): string {
  try {
    const date = new Date(timestamp)
    return `${date.toLocaleDateString('zh-CN')} ${date.toLocaleTimeString('zh-CN', {
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
    })}`
  } catch {
    return timestamp
  }
}

/** 功能：函数 truncateWorldId，负责 truncateWorldId 相关处理。 */
export function truncateWorldId(worldId: string): string {
  return worldId ? `${worldId.slice(0, 8)}...` : '未绑定'
}

/** 功能：函数 resolveWorldLabel，负责 resolveWorldLabel 相关处理。 */
export function resolveWorldLabel(worldId: string, worldLabelMap: Record<string, string>): string {
  if (!worldId) return '未绑定世界'
  return worldLabelMap[worldId] ?? truncateWorldId(worldId)
}

/** 功能：函数 toDistributionItems，负责 toDistributionItems 相关处理。 */
export function toDistributionItems(
  distribution: Record<string, number>,
  transformLabel?: (key: string) => string,
): AnalyticsDistributionItem[] {
  return Object.entries(distribution)
    .map(([key, value]) => ({
      key,
      label: transformLabel ? transformLabel(key) : key,
      value,
    }))
    .sort((left, right) => right.value - left.value)
}

/** 功能：函数 getDominantShare，负责 getDominantShare 相关处理。 */
export function getDominantShare(distribution: Record<string, number>): number {
  const values = Object.values(distribution)
  const total = values.reduce((sum, item) => sum + item, 0)
  if (!total || !values.length) return 0
  return Math.max(...values) / total
}
