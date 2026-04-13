/**
 * 文件说明：前端业务域逻辑与接口封装。
 */

import { useQuery } from '@tanstack/vue-query'
import { computed, unref, type MaybeRef } from 'vue'
import { getAnalyticsDaily } from '@/domains/analytics/api/analyticsTimeseriesApi'
import { ANALYTICS_KEYS } from '@/domains/analytics/queries/analyticsKeys'
import type { AnalyticsFilters } from '@/domains/analytics/types'

/** 处理 createFiltersKey 相关逻辑。 */
function createFiltersKey(filters: AnalyticsFilters) {
  return JSON.stringify({
    model: filters.model ?? '',
    world_id: filters.world_id ?? '',
    event_type: filters.event_type ?? '',
  })
}

/** 处理 useAnalyticsDailyQuery 相关逻辑。 */
export function useAnalyticsDailyQuery(days: MaybeRef<number>, filters: MaybeRef<AnalyticsFilters>) {
  return useQuery({
    queryKey: computed(() => ANALYTICS_KEYS.daily(unref(days), createFiltersKey(unref(filters)))),
    queryFn: () => getAnalyticsDaily(unref(days), unref(filters)),
  })
}
