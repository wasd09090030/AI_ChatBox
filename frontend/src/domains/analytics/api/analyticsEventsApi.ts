import api from '@/services/api'
import type { AnalyticsEvent, AnalyticsFilters } from '@/domains/analytics/types'

export async function getAnalyticsEvents(limit = 50, filters: AnalyticsFilters = {}): Promise<AnalyticsEvent[]> {
  const response = await api.get<{ events: AnalyticsEvent[] }>('/stats/log', { params: { limit, ...filters } })
  return response.data.events
}

