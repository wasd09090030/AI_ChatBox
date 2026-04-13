/**
 * 文件说明：前端业务域逻辑与接口封装。
 */

import { useQuery } from '@tanstack/vue-query'
import { getAnalyticsFilterOptions } from '@/domains/analytics/api/analyticsFilterOptionsApi'
import { ANALYTICS_KEYS } from '@/domains/analytics/queries/analyticsKeys'

/** 处理 useAnalyticsFilterOptionsQuery 相关逻辑。 */
export function useAnalyticsFilterOptionsQuery() {
  return useQuery({
    queryKey: ANALYTICS_KEYS.filterOptions,
    queryFn: getAnalyticsFilterOptions,
    refetchInterval: 30000,
  })
}