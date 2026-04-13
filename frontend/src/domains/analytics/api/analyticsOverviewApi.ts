/**
 * 文件说明：前端业务域逻辑与接口封装。
 */

import api from '@/services/api'
import type { AnalyticsFilters, AnalyticsOverview } from '@/domains/analytics/types'

/** 处理 getAnalyticsOverview 相关逻辑。 */
export async function getAnalyticsOverview(filters: AnalyticsFilters = {}): Promise<AnalyticsOverview> {
  const response = await api.get<AnalyticsOverview>('/stats/overview', { params: filters })
  return response.data
}
