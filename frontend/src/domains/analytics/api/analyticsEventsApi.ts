/**
 * 文件说明：前端业务域逻辑与接口封装。
 */

import api from '@/services/api'
import type { AnalyticsEvent, AnalyticsFilters } from '@/domains/analytics/types'

/** 处理 getAnalyticsEvents 相关逻辑。 */
export async function getAnalyticsEvents(limit = 50, filters: AnalyticsFilters = {}): Promise<AnalyticsEvent[]> {
  const response = await api.get<{ events: AnalyticsEvent[] }>('/stats/log', { params: { limit, ...filters } })
  return response.data.events
}

