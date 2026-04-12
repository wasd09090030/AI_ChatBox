/**
 * 文件说明：前端业务域逻辑与接口封装。
 */

import api from '@/services/api'
import type { AnalyticsFilterOptions } from '@/domains/analytics/types'

/** 功能：函数 getAnalyticsFilterOptions，负责 getAnalyticsFilterOptions 相关处理。 */
export async function getAnalyticsFilterOptions(): Promise<AnalyticsFilterOptions> {
  const response = await api.get<AnalyticsFilterOptions>('/stats/filter-options')
  return response.data
}