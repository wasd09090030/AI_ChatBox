import api from '@/services/api'
import type { AnalyticsDailyStat, AnalyticsFilters } from '@/domains/analytics/types'

export async function getAnalyticsDaily(days = 7, filters: AnalyticsFilters = {}): Promise<AnalyticsDailyStat[]> {
  const response = await api.get<AnalyticsDailyStat[]>('/stats/daily', { params: { days, ...filters } })
  return response.data
}
