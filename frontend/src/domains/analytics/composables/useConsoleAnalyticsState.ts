import { computed, ref } from 'vue'
import { useAnalyticsDailyQuery } from '@/domains/analytics/queries/useAnalyticsDailyQuery'
import { useAnalyticsEventsQuery } from '@/domains/analytics/queries/useAnalyticsEventsQuery'
import { useAnalyticsFilterOptionsQuery } from '@/domains/analytics/queries/useAnalyticsFilterOptionsQuery'
import { useAnalyticsOverviewQuery } from '@/domains/analytics/queries/useAnalyticsOverviewQuery'
import type { AnalyticsFilterOption, AnalyticsFilters, AnalyticsMetricItem } from '@/domains/analytics/types'
import {
  formatCompactNumber,
  formatPercent,
  formatSeconds,
  getDominantShare,
  resolveWorldLabel,
  toDistributionItems,
} from '@/domains/analytics/utils/formatters'
import { useWorldsQuery } from '@/domains/lorebook/queries/useLorebookQueries'

export function useConsoleAnalyticsState() {
  const days = ref('14')
  const eventsLimit = ref(50)
  const selectedModel = ref('all')
  const selectedWorldId = ref('all')
  const selectedEventType = ref('all')

  const filters = computed<AnalyticsFilters>(() => ({
    model: selectedModel.value === 'all' ? undefined : selectedModel.value,
    world_id: selectedWorldId.value === 'all' ? undefined : selectedWorldId.value,
    event_type: selectedEventType.value === 'all' ? undefined : selectedEventType.value,
  }))

  const { data: overview, isLoading: overviewLoading, refetch: refetchOverview } = useAnalyticsOverviewQuery(filters)
  const { data: daily, isLoading: dailyLoading, refetch: refetchDaily } = useAnalyticsDailyQuery(
    computed(() => Number(days.value)),
    filters,
  )
  const { data: events, isLoading: eventsLoading, refetch: refetchEvents } = useAnalyticsEventsQuery(eventsLimit, filters)
  const { data: filterOptions } = useAnalyticsFilterOptionsQuery()
  const { data: worlds } = useWorldsQuery()

  const worldLabelMap = computed<Record<string, string>>(() => {
    const items = worlds.value ?? []
    return Object.fromEntries(items.map((world) => [world.id, world.name]))
  })

  const modelDistributionItems = computed(() => toDistributionItems(overview.value?.model_distribution ?? {}))
  const eventTypeDistributionItems = computed(() => toDistributionItems(overview.value?.event_type_distribution ?? {}))
  const worldDistributionItems = computed(() => toDistributionItems(
    overview.value?.world_distribution ?? {},
    (worldId) => resolveWorldLabel(worldId, worldLabelMap.value),
  ))
  const tokenSourceDistributionItems = computed(() => toDistributionItems(
    overview.value?.token_source_distribution ?? {},
    (source) => source === 'provider_usage' ? 'Provider 真实用量' : '估算 token',
  ))

  const modelOptions = computed<AnalyticsFilterOption[]>(() => filterOptions.value?.models ?? [])
  const eventTypeOptions = computed<AnalyticsFilterOption[]>(() => filterOptions.value?.event_types ?? [])
  const worldOptions = computed(() => {
    const items = filterOptions.value?.world_ids ?? []
    return items.map((option) => ({
      ...option,
      label: resolveWorldLabel(option.value, worldLabelMap.value),
    }))
  })

  const topModelLabel = computed(() => modelDistributionItems.value[0]?.label ?? '暂无')
  const topWorldLabel = computed(() => worldDistributionItems.value[0]?.label ?? '未绑定世界')

  const metrics = computed<AnalyticsMetricItem[]>(() => {
    const currentOverview = overview.value
    if (!currentOverview) {
      return []
    }

    const modelDominance = getDominantShare(currentOverview.model_distribution)
    return [
      {
        key: 'requests',
        label: '总请求',
        value: formatCompactNumber(currentOverview.total_requests),
        caption: `成功 ${formatCompactNumber(currentOverview.success_requests)} / 失败 ${formatCompactNumber(currentOverview.error_requests)}`,
      },
      {
        key: 'success',
        label: '成功率',
        value: formatPercent(currentOverview.success_rate),
        caption: modelDominance > 0.7 ? '请求高度集中在少数模型，留意单模型风格锁定。' : '模型分布相对分散，适合横向比较效果。',
        accent: 'success',
      },
      {
        key: 'errors',
        label: '失败次数',
        value: formatCompactNumber(currentOverview.error_requests),
        caption: '失败抬头时先回到下方明细表，看是否某个模型或世界异常集中。',
        accent: currentOverview.error_requests > 0 ? 'danger' : 'default',
      },
      {
        key: 'inputTokens',
        label: 'Input Token',
        value: formatCompactNumber(currentOverview.total_input_tokens),
        caption: `平均每次 ${formatCompactNumber(currentOverview.avg_input_tokens)} token`,
        accent: 'info',
      },
      {
        key: 'outputTokens',
        label: 'Output Token',
        value: formatCompactNumber(currentOverview.total_output_tokens),
        caption: `平均每次 ${formatCompactNumber(currentOverview.avg_output_tokens)} token`,
        accent: 'warning',
      },
      {
        key: 'avgTokens',
        label: '单次总消耗',
        value: formatCompactNumber(currentOverview.avg_total_tokens),
        caption: `总体 ${formatCompactNumber(currentOverview.total_tokens)} token`,
      },
      {
        key: 'latency',
        label: '平均耗时',
        value: formatSeconds(currentOverview.avg_generation_time),
        caption: `Provider 覆盖率 ${formatPercent(currentOverview.provider_usage_rate)}`,
        accent: 'warning',
      },
      {
        key: 'retrieval',
        label: '设定命中',
        value: `${currentOverview.avg_retrieved_context_count.toFixed(1)} / ${currentOverview.avg_vector_hits.toFixed(1)}`,
        caption: '前者是上下文注入次数，后者是向量命中量；两者一起看，才知道设定有没有真正进入故事。',
        accent: 'info',
      },
    ]
  })

  const tokenMetrics = computed(() => metrics.value.filter((item) => (
    item.key === 'inputTokens' || item.key === 'outputTokens' || item.key === 'avgTokens'
  )))

  const overviewMetrics = computed(() => metrics.value.filter((item) => (
    item.key === 'requests'
    || item.key === 'success'
    || item.key === 'errors'
    || item.key === 'latency'
  )))

  const refreshing = computed(() => overviewLoading.value || dailyLoading.value || eventsLoading.value)

  async function refetchAll() {
    await Promise.all([refetchOverview(), refetchDaily(), refetchEvents()])
  }

  return {
    days,
    selectedModel,
    selectedWorldId,
    selectedEventType,
    overview,
    daily,
    events,
    overviewLoading,
    dailyLoading,
    eventsLoading,
    refreshing,
    worldLabelMap,
    modelDistributionItems,
    eventTypeDistributionItems,
    worldDistributionItems,
    tokenSourceDistributionItems,
    modelOptions,
    worldOptions,
    eventTypeOptions,
    topModelLabel,
    topWorldLabel,
    tokenMetrics,
    overviewMetrics,
    refetchAll,
  }
}
