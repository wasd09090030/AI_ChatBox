import api from '@/services/api'
import type { AnalyticsFilters, AnalyticsOverview } from '@/domains/analytics/types'

export async function getAnalyticsOverview(filters: AnalyticsFilters = {}): Promise<AnalyticsOverview> {
  const response = await api.get<AnalyticsOverview>('/stats/overview', { params: filters })
  return response.data
}
