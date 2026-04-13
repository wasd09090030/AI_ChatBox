/**
 * 文件说明：前端业务域逻辑与接口封装。
 */

import api from '@/services/api'
import type { AnalyticsDailyStat, AnalyticsFilters } from '@/domains/analytics/types'

/** 处理 getAnalyticsDaily 相关逻辑。 */
export async function getAnalyticsDaily(days = 7, filters: AnalyticsFilters = {}): Promise<AnalyticsDailyStat[]> {
  const response = await api.get<AnalyticsDailyStat[]>('/stats/daily', { params: { days, ...filters } })
  return response.data
}
