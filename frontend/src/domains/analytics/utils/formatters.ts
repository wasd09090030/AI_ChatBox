import type { AnalyticsDistributionItem } from '@/domains/analytics/types'

export function formatCompactNumber(value?: number | null): string {
  if (value == null) return '0'
  return new Intl.NumberFormat('zh-CN', {
    notation: value >= 1000 ? 'compact' : 'standard',
    maximumFractionDigits: value >= 1000 ? 1 : 0,
  }).format(value)
}

export function formatPercent(value?: number | null): string {
  if (value == null) return '0.0%'
  return `${(value * 100).toFixed(1)}%`
}

export function formatSeconds(value?: number | null): string {
  if (value == null) return '0.00s'
  return `${value.toFixed(2)}s`
}

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

export function truncateWorldId(worldId: string): string {
  return worldId ? `${worldId.slice(0, 8)}...` : '未绑定'
}

export function resolveWorldLabel(worldId: string, worldLabelMap: Record<string, string>): string {
  if (!worldId) return '未绑定世界'
  return worldLabelMap[worldId] ?? truncateWorldId(worldId)
}

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

export function getDominantShare(distribution: Record<string, number>): number {
  const values = Object.values(distribution)
  const total = values.reduce((sum, item) => sum + item, 0)
  if (!total || !values.length) return 0
  return Math.max(...values) / total
}
