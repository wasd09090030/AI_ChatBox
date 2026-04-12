/**
 * 文件说明：前端业务域逻辑与接口封装。
 */

import { useQuery } from '@tanstack/vue-query'
import { computed, unref, type MaybeRef } from 'vue'
import { getAnalyticsOverview } from '@/domains/analytics/api/analyticsOverviewApi'
import { ANALYTICS_KEYS } from '@/domains/analytics/queries/analyticsKeys'
import type { AnalyticsFilters } from '@/domains/analytics/types'

/** 功能：函数 createFiltersKey，负责 createFiltersKey 相关处理。 */
function createFiltersKey(filters: AnalyticsFilters) {
  return JSON.stringify({
    model: filters.model ?? '',
    world_id: filters.world_id ?? '',
    event_type: filters.event_type ?? '',
  })
}

/** 功能：函数 useAnalyticsOverviewQuery，负责 useAnalyticsOverviewQuery 相关处理。 */
export function useAnalyticsOverviewQuery(filters: MaybeRef<AnalyticsFilters>) {
  return useQuery({
    queryKey: computed(() => ANALYTICS_KEYS.overview(createFiltersKey(unref(filters)))),
    queryFn: () => getAnalyticsOverview(unref(filters)),
    refetchInterval: 30000,
  })
}
