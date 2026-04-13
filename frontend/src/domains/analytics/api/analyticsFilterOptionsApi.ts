/**
 * 文件说明：前端业务域逻辑与接口封装。
 */

import api from '@/services/api'
import type { AnalyticsFilterOptions } from '@/domains/analytics/types'

/** 处理 getAnalyticsFilterOptions 相关逻辑。 */
export async function getAnalyticsFilterOptions(): Promise<AnalyticsFilterOptions> {
  const response = await api.get<AnalyticsFilterOptions>('/stats/filter-options')
  return response.data
}