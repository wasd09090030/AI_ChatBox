import { useQuery } from '@tanstack/vue-query'
import { computed, unref, type MaybeRef } from 'vue'
import { getAnalyticsEvents } from '@/domains/analytics/api/analyticsEventsApi'
import { ANALYTICS_KEYS } from '@/domains/analytics/queries/analyticsKeys'
import type { AnalyticsFilters } from '@/domains/analytics/types'

function createFiltersKey(filters: AnalyticsFilters) {
  return JSON.stringify({
    model: filters.model ?? '',
    world_id: filters.world_id ?? '',
    event_type: filters.event_type ?? '',
  })
}

export function useAnalyticsEventsQuery(limit: MaybeRef<number>, filters: MaybeRef<AnalyticsFilters>) {
  return useQuery({
    queryKey: computed(() => ANALYTICS_KEYS.events(unref(limit), createFiltersKey(unref(filters)))),
    queryFn: () => getAnalyticsEvents(unref(limit), unref(filters)),
    refetchInterval: 30000,
  })
}

