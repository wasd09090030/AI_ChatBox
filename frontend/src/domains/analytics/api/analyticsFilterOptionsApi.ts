import api from '@/services/api'
import type { AnalyticsFilterOptions } from '@/domains/analytics/types'

export async function getAnalyticsFilterOptions(): Promise<AnalyticsFilterOptions> {
  const response = await api.get<AnalyticsFilterOptions>('/stats/filter-options')
  return response.data
}