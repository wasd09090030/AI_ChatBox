import { useQuery } from '@tanstack/vue-query'
import { getAnalyticsFilterOptions } from '@/domains/analytics/api/analyticsFilterOptionsApi'
import { ANALYTICS_KEYS } from '@/domains/analytics/queries/analyticsKeys'

export function useAnalyticsFilterOptionsQuery() {
  return useQuery({
    queryKey: ANALYTICS_KEYS.filterOptions,
    queryFn: getAnalyticsFilterOptions,
    refetchInterval: 30000,
  })
}