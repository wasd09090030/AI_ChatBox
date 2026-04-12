/**
 * 文件说明：前端业务域逻辑与接口封装。
 */

import api from '@/services/api'
import type { AnalyticsEvent, AnalyticsFilters } from '@/domains/analytics/types'

/** 功能：函数 getAnalyticsEvents，负责 getAnalyticsEvents 相关处理。 */
export async function getAnalyticsEvents(limit = 50, filters: AnalyticsFilters = {}): Promise<AnalyticsEvent[]> {
  const response = await api.get<{ events: AnalyticsEvent[] }>('/stats/log', { params: { limit, ...filters } })
  return response.data.events
}

