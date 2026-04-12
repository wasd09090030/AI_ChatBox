<script setup lang="ts">
// 文件说明：前端页面级视图编排。
import { storeToRefs } from 'pinia'
import { computed, ref, watch } from 'vue'
import {
  AlertTriangle,
  ArrowLeftRight,
  Brain,
  CalendarRange,
  ChevronLeft,
  ChevronRight,
  Filter,
  MapPinned,
  Package,
  RefreshCw,
  Search,
  Sparkles,
  UserRound,
  Users,
} from 'lucide-vue-next'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import {
  useMemoryUpdatesQuery,
  useSessionMemoryTimelineQuery,
  useSessionStoryMemoryQuery,
} from '@/domains/memory/queries/useMemoryUpdateQueries'
import { useWorldsQuery } from '@/domains/lorebook/queries/useLorebookQueries'
import type { MemoryUpdateTimelineItem } from '@/domains/memory/api/memoryUpdatesApi'
import {
  deriveSummaryLifecycleState,
  formatMemoryPayloadFields,
  getMemoryActionLabel,
  getMemoryLayerLabel,
  getMemorySourceLabel,
  getMemoryStatusLabel,
  getSummaryLifecycleDescriptor,
  groupMemoryEventsByOperation,
  type SummaryLifecycleState,
} from '@/domains/memory/memoryUpdatePresentation'
import {
  extractWorldUpdateHighlights,
  formatEntityPatchValue,
  getEntityPatchChangeSummary,
  getEntityPatchCommittedAt,
  getEntityPatchEntityLabel,
  getEntityPatchEvidenceText,
  getEntityPatchEventId,
  getEntityPatchFieldLabel,
  getEntityPatchSourceTurn,
} from '@/domains/story/entityPatchPresentation'
import {
  getStoryMemoryEntitySnapshot,
  getStoryMemoryEntityUpdates,
  getStoryMemorySummarySnapshot,
  getStoryMemoryTimelineEvents,
  getStoryMemoryWorldUpdate,
} from '@/domains/story/storyMemoryPayload'
import { useMemoryUpdateDashboardStore } from '@/stores/memoryUpdateDashboard'
import { useStorySessionStore } from '@/stores/storySession'

// 变量作用：变量 storySessionStore，用于 storySessionStore 相关配置或状态。
const storySessionStore = useStorySessionStore()
// 变量作用：变量 dashboardStore，用于 dashboardStore 相关配置或状态。
const dashboardStore = useMemoryUpdateDashboardStore()

const {
  searchTerm,
  selectedSource,
  selectedLayer,
  selectedStatus,
  selectedTimeRange,
  selectedSessionId,
  detailPage,
  detailPageSize,
  listSnapshot,
  queryFilters,
} = storeToRefs(dashboardStore)

// 变量作用：变量 sourceOptions，用于 sourceOptions 相关配置或状态。
const sourceOptions = [
  { value: 'all', label: '全部来源' },
  { value: 'generate', label: '正常生成' },
  { value: 'rollback', label: '回滚修复' },
  { value: 'regenerate', label: '重生成修复' },
  { value: 'story_adjustment_commit', label: '正文调整提交' },
] as const

// 变量作用：变量 layerOptions，用于 layerOptions 相关配置或状态。
const layerOptions = [
  { value: 'all', label: '全部层级' },
  { value: 'episodic', label: '剧情记录' },
  { value: 'semantic', label: '摘要语义' },
  { value: 'entity_state', label: '实体状态' },
] as const

// 变量作用：变量 statusOptions，用于 statusOptions 相关配置或状态。
const statusOptions = [
  { value: 'all', label: '全部状态' },
  { value: 'committed', label: '正常' },
  { value: 'failed', label: '失败' },
  { value: 'stale', label: '已过期' },
] as const

// 变量作用：变量 timeRangeOptions，用于 timeRangeOptions 相关配置或状态。
const timeRangeOptions = [
  { value: 'all', label: '全部时间' },
  { value: '1h', label: '最近 1 小时' },
  { value: '24h', label: '最近 24 小时' },
  { value: '7d', label: '最近 7 天' },
] as const

// 变量作用：变量 pageSizeOptions，用于 pageSizeOptions 相关配置或状态。
const pageSizeOptions = [
  { value: '20', label: '20 条/页' },
  { value: '50', label: '50 条/页' },
  { value: '100', label: '100 条/页' },
] as const

// 变量作用：变量 expandedTextState，用于 expandedTextState 相关配置或状态。
const expandedTextState = ref<Record<string, boolean>>({})

// 变量作用：变量 summaries，用于 summaries 相关配置或状态。
const summaries = computed(() => storySessionStore.getAllSummaries())
// 变量作用：变量 summaryMap，用于 summaryMap 相关配置或状态。
const summaryMap = computed(() => new Map(summaries.value.map((record) => [record.sessionId, record])))
// 变量作用：变量 storyMemorySessionMap，用于 storyMemorySessionMap 相关配置或状态。
const storyMemorySessionMap = computed(() => new Map(
  storySessionStore.getAllStoryMemorySessions().map((record) => [record.sessionId, record]),
))
const { data: worlds } = useWorldsQuery()
// 变量作用：变量 worldNameMap，用于 worldNameMap 相关配置或状态。
const worldNameMap = computed(() => new Map((worlds.value ?? []).map((world) => [world.id, world.name])))

const {
  data: listResponse,
  isLoading: listLoading,
  isFetching: listFetching,
  error: listError,
  refetch: refetchList,
} = useMemoryUpdatesQuery(queryFilters)

// 变量作用：变量 listErrorMessage，用于 listErrorMessage 相关配置或状态。
const listErrorMessage = computed(() => (
  listError.value instanceof Error ? listError.value.message : '无法获取服务端记忆事件列表。'
))
// 变量作用：变量 effectiveListResponse，用于 effectiveListResponse 相关配置或状态。
const effectiveListResponse = computed(() => listResponse.value ?? listSnapshot.value ?? null)

/** 功能：函数 resolveSessionCardState，负责 resolveSessionCardState 相关处理。 */
function resolveSessionCardState(
  events: MemoryUpdateTimelineItem[],
  sessionId: string,
  summaryRecord: (typeof summaries.value)[number] | null,
): SummaryLifecycleState {
  const summarySnapshot = summaryRecord
    ? {
        summary_text: summaryRecord.summary_text,
        key_facts: summaryRecord.key_facts,
        last_turn: summaryRecord.last_turn,
        session_id: sessionId,
      }
    : null
  const derived = deriveSummaryLifecycleState(events, summarySnapshot)
  if (derived !== 'absent') return derived
  if (events.some((event) => event.memory_layer === 'semantic' && event.action === 'created')) return 'created'
  return storySessionStore.getRuntimeSummaryState(sessionId)
}

/** 功能：函数 buildEventHeadline，负责 buildEventHeadline 相关处理。 */
function buildEventHeadline(event: Pick<MemoryUpdateTimelineItem, 'memory_layer' | 'action'>) {
  return `${getMemoryLayerLabel(event.memory_layer)}：${getMemoryActionLabel(event.action)}`
}

/** 功能：函数 compactText，负责 compactText 相关处理。 */
function compactText(value: string, maxLength = 88) {
  const normalized = value.trim()
  return normalized.length > maxLength ? `${normalized.slice(0, maxLength - 1)}…` : normalized
}

/** 功能：函数 isTextTruncated，负责 isTextTruncated 相关处理。 */
function isTextTruncated(value: string, maxLength = 88) {
  return value.trim().length > maxLength
}

/** 功能：函数 isTextExpanded，负责 isTextExpanded 相关处理。 */
function isTextExpanded(key: string) {
  return Boolean(expandedTextState.value[key])
}

/** 功能：函数 toggleTextExpansion，负责 toggleTextExpansion 相关处理。 */
function toggleTextExpansion(key: string) {
  expandedTextState.value = {
    ...expandedTextState.value,
    [key]: !expandedTextState.value[key],
  }
}

/** 功能：函数 getExpandableText，负责 getExpandableText 相关处理。 */
function getExpandableText(key: string, value: string, maxLength = 88) {
  const normalized = value.trim()
  if (!normalized) return ''
  if (isTextExpanded(key) || !isTextTruncated(normalized, maxLength)) return normalized
  return compactText(normalized, maxLength)
}

/** 功能：函数 resolveWorldDisplay，负责 resolveWorldDisplay 相关处理。 */
function resolveWorldDisplay(worldId?: string | null) {
  const normalizedWorldId = (worldId ?? '').trim()
  if (!normalizedWorldId) return '未绑定世界'
  const worldName = worldNameMap.value.get(normalizedWorldId)
  if (!worldName) return normalizedWorldId
  return `${worldName} · ${normalizedWorldId}`
}

/** 功能：函数 formatTimestamp，负责 formatTimestamp 相关处理。 */
function formatTimestamp(value?: string | null) {
  if (!value) return '未知时间'
  try {
    return new Date(value).toLocaleString('zh-CN', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
    })
  } catch {
    return value
  }
}

/** 功能：函数 statusBadgeClass，负责 statusBadgeClass 相关处理。 */
function statusBadgeClass(status?: string | null) {
  if (status === 'failed') return 'border-rose-200 bg-rose-50 text-rose-700'
  if (status === 'stale') return 'border-amber-200 bg-amber-50 text-amber-700'
  return 'border-emerald-200 bg-emerald-50 text-emerald-700'
}

/** 功能：函数 layerBadgeClass，负责 layerBadgeClass 相关处理。 */
function layerBadgeClass(layer: string) {
  if (layer === 'semantic') return 'border-violet-200 bg-violet-50 text-violet-700'
  if (layer === 'episodic') return 'border-sky-200 bg-sky-50 text-sky-700'
  if (layer === 'entity_state') return 'border-orange-200 bg-orange-50 text-orange-700'
  return 'border-stone-200 bg-stone-50 text-stone-700'
}

/** 功能：函数 previewPayloadFields，负责 previewPayloadFields 相关处理。 */
function previewPayloadFields(payload?: Record<string, unknown> | null, limit = 2) {
  return formatMemoryPayloadFields(payload)
    .slice(0, limit)
}

/** 功能：函数 summarizeOperation，负责 summarizeOperation 相关处理。 */
function summarizeOperation(events: MemoryUpdateTimelineItem[]) {
  const segments = [
    { layer: 'semantic', count: events.filter((event) => event.memory_layer === 'semantic').length },
    { layer: 'entity_state', count: events.filter((event) => event.memory_layer === 'entity_state').length },
    { layer: 'episodic', count: events.filter((event) => event.memory_layer === 'episodic').length },
  ].filter((item) => item.count > 0)

  if (!segments.length) return '本批次没有可识别的结构化变动。'
  return segments.map((item) => `${getMemoryLayerLabel(item.layer)} ${item.count} 条`).join('，')
}

// 变量作用：变量 sessionCards，用于 sessionCards 相关配置或状态。
const sessionCards = computed(() => {
  const grouped = new Map<string, MemoryUpdateTimelineItem[]>()
  for (const item of effectiveListResponse.value?.items ?? []) {
    const bucket = grouped.get(item.session_id) ?? []
    bucket.push(item)
    grouped.set(item.session_id, bucket)
  }

  return Array.from(grouped.entries())
    .map(([sessionId, events]) => {
      const summary = summaryMap.value.get(sessionId) ?? null
      const storyMemorySession = storyMemorySessionMap.value.get(sessionId) ?? null
      const storyMemory = storyMemorySession?.storyMemory ?? null
      const entitySnapshot = getStoryMemoryEntitySnapshot(storyMemory)
      const memoryEvents = getStoryMemoryTimelineEvents(storyMemory, 200)
      const effectiveEvents = memoryEvents.length ? memoryEvents : events
      const latestEvent = [...effectiveEvents].sort((a, b) => b.committed_at.localeCompare(a.committed_at))[0] ?? null
      const latestWorldId = [...events].sort((a, b) => b.committed_at.localeCompare(a.committed_at))[0]?.world_id ?? ''
      const summaryState = resolveSessionCardState(effectiveEvents, sessionId, summary)
      const summaryDescriptor = getSummaryLifecycleDescriptor(summaryState)
      return {
        sessionId,
        summary,
        summaryDescriptor,
        storyTitle: storyMemorySession?.storyTitle ?? summary?.storyTitle ?? sessionId,
        worldId: storyMemory?.world_id ?? latestWorldId ?? summary?.worldId ?? '',
        latestEvent,
        latestEventHeadline: latestEvent ? buildEventHeadline(latestEvent) : '暂无变化',
        latestReason: latestEvent?.reason?.trim() || latestEvent?.title || '最近一次变动没有额外说明。',
        eventCount: effectiveEvents.length,
        semanticCount: effectiveEvents.filter((item) => item.memory_layer === 'semantic').length,
        trackedEntities: entitySnapshot?.total ?? 0,
        hasFailed: storyMemory?.operation?.status === 'failed' || effectiveEvents.some((item) => item.status === 'failed'),
      }
    })
    .sort((a, b) => (b.latestEvent?.committed_at ?? '').localeCompare(a.latestEvent?.committed_at ?? ''))
})

// 变量作用：变量 failedSessionCount，用于 failedSessionCount 相关配置或状态。
const failedSessionCount = computed(() => sessionCards.value.filter((item) => item.hasFailed).length)

watch(sessionCards, (items) => {
  if (!items.length) {
    dashboardStore.setSelectedSessionId(null)
    return
  }
  if (!selectedSessionId.value || !items.some((item) => item.sessionId === selectedSessionId.value)) {
    dashboardStore.setSelectedSessionId(items[0]?.sessionId ?? null)
  }
}, { immediate: true })

watch(listResponse, (value) => {
  dashboardStore.setListSnapshot(value)
}, { immediate: true })

watch(selectedSessionId, () => {
  dashboardStore.resetDetailState()
})

watch(detailPageSize, (value, oldValue) => {
  if (value !== oldValue) {
    dashboardStore.setDetailPage(1)
  }
})

const {
  data: timelineResponse,
  isLoading: timelineLoading,
  isFetching: timelineFetching,
  error: timelineError,
  refetch: refetchTimeline,
} = useSessionMemoryTimelineQuery(selectedSessionId, detailPage, detailPageSize)

// 变量作用：变量 timelineErrorMessage，用于 timelineErrorMessage 相关配置或状态。
const timelineErrorMessage = computed(() => (
  timelineError.value instanceof Error ? timelineError.value.message : '无法获取当前 session 的时间线。'
))
// 变量作用：变量 effectiveTimelineResponse，用于 effectiveTimelineResponse 相关配置或状态。
const effectiveTimelineResponse = computed(() => (
  timelineResponse.value ?? dashboardStore.getTimelineSnapshot(selectedSessionId.value)
))

watch(timelineResponse, (value) => {
  if (selectedSessionId.value) {
    dashboardStore.setTimelineSnapshot(selectedSessionId.value, value)
  }
}, { immediate: true })

const {
  data: storyMemoryResponse,
  isFetching: storyMemoryFetching,
  refetch: refetchStoryMemory,
} = useSessionStoryMemoryQuery(selectedSessionId, detailPage, detailPageSize)

// 变量作用：变量 effectiveStoryMemoryResponse，用于 effectiveStoryMemoryResponse 相关配置或状态。
const effectiveStoryMemoryResponse = computed(() => (
  storyMemoryResponse.value ?? dashboardStore.getStoryMemorySnapshot(selectedSessionId.value)
))

watch(storyMemoryResponse, (value) => {
  if (selectedSessionId.value) {
    dashboardStore.setStoryMemorySnapshot(selectedSessionId.value, value)
    if (value?.story_memory) {
      const currentSessionId = selectedSessionId.value
      const localStoryMemorySession = storyMemorySessionMap.value.get(currentSessionId) ?? null
      const localSummary = summaryMap.value.get(currentSessionId) ?? null
      storySessionStore.upsertStoryMemorySession(
        currentSessionId,
        localStoryMemorySession?.storyTitle ?? localSummary?.storyTitle ?? '',
        value.world_id ?? localStoryMemorySession?.worldId ?? localSummary?.worldId ?? '',
        value.story_memory,
      )
    }
  }
}, { immediate: true })

// 变量作用：变量 selectedSessionCard，用于 selectedSessionCard 相关配置或状态。
const selectedSessionCard = computed(() => (
  sessionCards.value.find((item) => item.sessionId === selectedSessionId.value) ?? null
))

// 变量作用：变量 selectedStoryMemory，用于 selectedStoryMemory 相关配置或状态。
const selectedStoryMemory = computed(() => {
  if (effectiveStoryMemoryResponse.value?.story_memory) {
    return effectiveStoryMemoryResponse.value.story_memory
  }
  if (!selectedSessionId.value) return null
  return storySessionStore.getStoryMemorySession(selectedSessionId.value)?.storyMemory ?? null
})

// 变量作用：变量 selectedSummarySnapshot，用于 selectedSummarySnapshot 相关配置或状态。
const selectedSummarySnapshot = computed(() => {
  const summaryFromMemory = getStoryMemorySummarySnapshot(selectedStoryMemory.value)
  if (summaryFromMemory) return summaryFromMemory
  const summary = selectedSessionCard.value?.summary
  if (!summary || !selectedSessionId.value) return null
  return {
    summary_text: summary.summary_text,
    key_facts: summary.key_facts,
    last_turn: summary.last_turn,
    session_id: selectedSessionId.value,
  }
})

// 变量作用：变量 selectedTimelineEvents，用于 selectedTimelineEvents 相关配置或状态。
const selectedTimelineEvents = computed(() => {
  const timelineFromMemory = getStoryMemoryTimelineEvents(selectedStoryMemory.value, detailPageSize.value)
  if (timelineFromMemory.length) return timelineFromMemory
  return effectiveTimelineResponse.value?.items ?? []
})

// 变量作用：变量 detailSummaryDescriptor，用于 detailSummaryDescriptor 相关配置或状态。
const detailSummaryDescriptor = computed(() => {
  const state = effectiveTimelineResponse.value?.summary_state.state
    ?? deriveSummaryLifecycleState(selectedTimelineEvents.value, selectedSummarySnapshot.value)
  const reason = effectiveTimelineResponse.value?.summary_state.last_semantic_event?.reason
    ?? semanticEvents.value[0]?.reason
    ?? null
  return getSummaryLifecycleDescriptor(state, { reason })
})

// 变量作用：变量 operationGroups，用于 operationGroups 相关配置或状态。
const operationGroups = computed(() => groupMemoryEventsByOperation(selectedTimelineEvents.value))
// 变量作用：变量 semanticEvents，用于 semanticEvents 相关配置或状态。
const semanticEvents = computed(() => selectedTimelineEvents.value.filter((event) => event.memory_layer === 'semantic'))
// 变量作用：变量 failedEvents，用于 failedEvents 相关配置或状态。
const failedEvents = computed(() => selectedTimelineEvents.value.filter((event) => event.status === 'failed'))
// 变量作用：变量 latestTimelineEvent，用于 latestTimelineEvent 相关配置或状态。
const latestTimelineEvent = computed(() => {
  const items = selectedTimelineEvents.value
  return [...items].sort((a, b) => b.committed_at.localeCompare(a.committed_at))[0] ?? null
})

// 变量作用：变量 selectedEntitySnapshot，用于 selectedEntitySnapshot 相关配置或状态。
const selectedEntitySnapshot = computed(() => {
  const storyMemorySnapshot = getStoryMemoryEntitySnapshot(selectedStoryMemory.value)
  if (storyMemorySnapshot) return storyMemorySnapshot
  return selectedSessionId.value ? storySessionStore.getEntityStateSnapshot(selectedSessionId.value) : null
})

// 变量作用：变量 selectedEntityPatchUpdates，用于 selectedEntityPatchUpdates 相关配置或状态。
const selectedEntityPatchUpdates = computed(() => {
  const storyMemoryUpdates = getStoryMemoryEntityUpdates(selectedStoryMemory.value, 50)
  if (storyMemoryUpdates.length) return storyMemoryUpdates
  return selectedSessionId.value ? storySessionStore.getSessionEntityStateUpdates(selectedSessionId.value, 50) : []
})

// 变量作用：变量 selectedWorldUpdate，用于 selectedWorldUpdate 相关配置或状态。
const selectedWorldUpdate = computed(() => {
  const storyMemoryWorldUpdate = getStoryMemoryWorldUpdate(selectedStoryMemory.value)
  if (storyMemoryWorldUpdate) return storyMemoryWorldUpdate
  return selectedSessionId.value ? storySessionStore.getSessionWorldUpdate(selectedSessionId.value)?.payload ?? null : null
})

// 变量作用：变量 selectedEntityNameMap，用于 selectedEntityNameMap 相关配置或状态。
const selectedEntityNameMap = computed(() => new Map(
  (selectedEntitySnapshot.value?.items ?? []).map((item) => [item.entity_id, item.display_name]),
))

// 变量作用：变量 selectedEntityWarnings，用于 selectedEntityWarnings 相关配置或状态。
const selectedEntityWarnings = computed(() => {
  const items = selectedEntitySnapshot.value?.items ?? []
  if (!items.length) return ['当前会话还没有缓存到实体状态快照。']

  const warnings: string[] = []
  const missingLocation = items.filter((item) => !item.current_location)
  if (missingLocation.length) {
    warnings.push(`仍有角色缺少明确位置：${missingLocation.slice(0, 4).map((item) => item.display_name).join('、')}`)
  }
  const missingEvidence = items.filter((item) => !item.evidence.length)
  if (missingEvidence.length) {
    warnings.push(`仍有角色缺少证据：${missingEvidence.slice(0, 4).map((item) => item.display_name).join('、')}`)
  }
  const unresolvedCompanions = items
    .flatMap((item) => item.companions.map((companionId) => ({ owner: item.display_name, companionId })))
    .filter((item) => !selectedEntityNameMap.value.has(item.companionId))
  if (unresolvedCompanions.length) {
    warnings.push(`存在未解析同行引用，最近来自：${unresolvedCompanions[0]?.owner ?? '未知角色'}`)
  }
  return warnings.slice(0, 3)
})

// 变量作用：变量 selectedEntityLocationCount，用于 selectedEntityLocationCount 相关配置或状态。
const selectedEntityLocationCount = computed(() => new Set(
  (selectedEntitySnapshot.value?.items ?? []).map((item) => item.current_location).filter(Boolean),
).size)
// 变量作用：变量 selectedWorldUpdateHighlights，用于 selectedWorldUpdateHighlights 相关配置或状态。
const selectedWorldUpdateHighlights = computed(() => extractWorldUpdateHighlights(selectedWorldUpdate.value).slice(0, 4))

// 变量作用：变量 recentEntityChangeGroups，用于 recentEntityChangeGroups 相关配置或状态。
const recentEntityChangeGroups = computed(() => {
  const grouped = new Map<string, {
    id: string
    entityLabel: string
    committedAt: string
    sourceTurn: number | null
    changes: Array<{
      id: string
      fieldLabel: string
      summary: string
      beforeText: string
      afterText: string
    }>
    evidence: string[]
  }>()

  for (const patch of selectedEntityPatchUpdates.value.slice(0, 18)) {
    const entityLabel = getEntityPatchEntityLabel(patch)
    const group = grouped.get(entityLabel) ?? {
      id: entityLabel,
      entityLabel,
      committedAt: getEntityPatchCommittedAt(patch),
      sourceTurn: getEntityPatchSourceTurn(patch),
      changes: [],
      evidence: [],
    }
    group.committedAt = group.committedAt > getEntityPatchCommittedAt(patch)
      ? group.committedAt
      : getEntityPatchCommittedAt(patch)
    group.sourceTurn = getEntityPatchSourceTurn(patch) ?? group.sourceTurn
    const beforeRaw = patch.before ?? (patch.op === 'remove' ? patch.value : null)
    const afterRaw = patch.after ?? (patch.op !== 'remove' ? patch.value : null)
    if (!group.changes.some((item) => item.id === getEntityPatchEventId(patch))) {
      group.changes.push({
        id: getEntityPatchEventId(patch),
        fieldLabel: getEntityPatchFieldLabel(patch),
        summary: getEntityPatchChangeSummary(patch),
        beforeText: formatEntityPatchValue(beforeRaw),
        afterText: formatEntityPatchValue(afterRaw),
      })
    }
    const evidence = getEntityPatchEvidenceText(patch)
    if (evidence && !group.evidence.includes(evidence)) {
      group.evidence.push(evidence)
    }
    grouped.set(entityLabel, group)
  }

  return Array.from(grouped.values())
    .sort((a, b) => b.committedAt.localeCompare(a.committedAt))
    .slice(0, 6)
})

// 变量作用：变量 latestSemanticEvent，用于 latestSemanticEvent 相关配置或状态。
const latestSemanticEvent = computed(() => (
  effectiveTimelineResponse.value?.summary_state.last_semantic_event
  ?? semanticEvents.value[0]
  ?? null
))

// 变量作用：变量 detailTotal，用于 detailTotal 相关配置或状态。
const detailTotal = computed(() => (
  effectiveStoryMemoryResponse.value?.timeline_total
  ?? effectiveTimelineResponse.value?.total
  ?? selectedTimelineEvents.value.length
))
// 变量作用：变量 detailPageCount，用于 detailPageCount 相关配置或状态。
const detailPageCount = computed(() => Math.max(1, Math.ceil(detailTotal.value / detailPageSize.value)))
// 变量作用：变量 historyRangeLabel，用于 historyRangeLabel 相关配置或状态。
const historyRangeLabel = computed(() => {
  if (!detailTotal.value) return '暂无历史记录'
  const start = (detailPage.value - 1) * detailPageSize.value + 1
  const end = Math.min(detailTotal.value, detailPage.value * detailPageSize.value)
  return `第 ${start}-${end} 条，共 ${detailTotal.value} 条`
})

watch(detailPageCount, (count) => {
  if (detailPage.value > count) {
    dashboardStore.setDetailPage(count)
  }
}, { immediate: true })

/** 功能：函数 goToPreviousPage，负责 goToPreviousPage 相关处理。 */
function goToPreviousPage() {
  if (detailPage.value > 1) {
    dashboardStore.setDetailPage(detailPage.value - 1)
  }
}

/** 功能：函数 goToNextPage，负责 goToNextPage 相关处理。 */
function goToNextPage() {
  if (detailPage.value < detailPageCount.value) {
    dashboardStore.setDetailPage(detailPage.value + 1)
  }
}

/** 功能：函数 resolveEntityCompanionLabel，负责 resolveEntityCompanionLabel 相关处理。 */
function resolveEntityCompanionLabel(companionId: string) {
  return selectedEntityNameMap.value.get(companionId) ?? companionId
}
</script>

<template>
  <div class="flex-1 overflow-auto bg-background">
    <div class="mx-auto w-full max-w-[1500px] px-4 py-4 sm:px-6 sm:py-6">
      <section class="rounded-[32px] border border-border bg-background p-4 shadow-sm sm:p-6">
        <div class="grid gap-6 xl:grid-cols-[360px_minmax(0,1fr)]">
          <aside class="space-y-5">
            <section class="rounded-[28px] border border-border bg-background p-6">
              <div class="inline-flex items-center gap-2 rounded-full border border-stone-300/80 bg-white/85 px-3 py-1 text-[11px] font-medium uppercase tracking-[0.24em] text-stone-700">
                <Sparkles class="h-3.5 w-3.5" />
                Story Memory Ledger
              </div>
              <h1 class="hero-title mt-5 text-3xl text-stone-950">故事记忆总览</h1>
              <p class="mt-3 text-sm leading-6 text-stone-700">
                先看当前状态，再看本轮变化，最后翻历史。默认隐藏复杂标识，只保留真正有判断价值的信息。
              </p>

              <div class="mt-6 grid gap-3 sm:grid-cols-2 xl:grid-cols-1">
                <div class="memory-stat rounded-[22px] border border-stone-200/80 p-4">
                  <p class="text-[11px] uppercase tracking-[0.22em] text-stone-500">当前命中会话</p>
                  <p class="mt-2 text-2xl font-semibold text-stone-950">{{ sessionCards.length }}</p>
                </div>
                <div class="memory-stat rounded-[22px] border border-stone-200/80 p-4">
                  <p class="text-[11px] uppercase tracking-[0.22em] text-stone-500">命中变动条数</p>
                  <p class="mt-2 text-2xl font-semibold text-stone-950">{{ effectiveListResponse?.total ?? 0 }}</p>
                </div>
                <div class="memory-stat rounded-[22px] border border-stone-200/80 p-4">
                  <p class="text-[11px] uppercase tracking-[0.22em] text-stone-500">本地摘要快照</p>
                  <p class="mt-2 text-2xl font-semibold text-stone-950">{{ summaries.length }}</p>
                </div>
                <div class="memory-stat rounded-[22px] border border-stone-200/80 p-4">
                  <p class="text-[11px] uppercase tracking-[0.22em] text-stone-500">异常会话</p>
                  <p class="mt-2 text-2xl font-semibold text-stone-950">{{ failedSessionCount }}</p>
                </div>
              </div>
            </section>

            <Card class="rounded-[28px] border-stone-200/80 bg-white/90 shadow-none">
              <CardHeader class="gap-4">
                <div class="flex items-start justify-between gap-3">
                  <div>
                    <CardTitle class="flex items-center gap-2 text-stone-950">
                      <Filter class="h-4 w-4 text-stone-600" />
                      筛选会话
                    </CardTitle>
                    <CardDescription>先定位会话，再到右侧查看当前状态、本轮变化和历史翻页。</CardDescription>
                  </div>
                  <Button
                    variant="outline"
                    size="sm"
                    class="rounded-full border-stone-300 bg-white/90 text-stone-700"
                    @click="() => { refetchList(); refetchTimeline(); refetchStoryMemory() }"
                  >
                    <RefreshCw class="h-3.5 w-3.5" :class="{ 'animate-spin': listFetching || timelineFetching || storyMemoryFetching }" />
                    刷新
                  </Button>
                </div>
              </CardHeader>

              <CardContent class="space-y-4">
                <div class="relative">
                  <Search class="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-stone-400" />
                  <Input
                    v-model="searchTerm"
                    class="h-11 rounded-2xl border-stone-200 bg-stone-50/60 pl-9"
                    placeholder="按标题、session、世界或原因搜索"
                  />
                </div>

                <div class="grid gap-3 sm:grid-cols-2">
                  <Select v-model="selectedSource">
                    <SelectTrigger class="h-11 rounded-2xl border-stone-200 bg-stone-50/60">
                      <SelectValue placeholder="来源" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem v-for="option in sourceOptions" :key="option.value" :value="option.value">
                        {{ option.label }}
                      </SelectItem>
                    </SelectContent>
                  </Select>

                  <Select v-model="selectedLayer">
                    <SelectTrigger class="h-11 rounded-2xl border-stone-200 bg-stone-50/60">
                      <SelectValue placeholder="层级" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem v-for="option in layerOptions" :key="option.value" :value="option.value">
                        {{ option.label }}
                      </SelectItem>
                    </SelectContent>
                  </Select>

                  <Select v-model="selectedStatus">
                    <SelectTrigger class="h-11 rounded-2xl border-stone-200 bg-stone-50/60">
                      <SelectValue placeholder="状态" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem v-for="option in statusOptions" :key="option.value" :value="option.value">
                        {{ option.label }}
                      </SelectItem>
                    </SelectContent>
                  </Select>

                  <Select v-model="selectedTimeRange">
                    <SelectTrigger class="h-11 rounded-2xl border-stone-200 bg-stone-50/60">
                      <SelectValue placeholder="时间范围" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem v-for="option in timeRangeOptions" :key="option.value" :value="option.value">
                        {{ option.label }}
                      </SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                <div v-if="listLoading && !effectiveListResponse" class="rounded-[22px] border border-dashed border-stone-300 bg-stone-50/70 px-4 py-10 text-center text-sm text-stone-500">
                  正在加载服务端记忆数据…
                </div>

                <div v-else-if="listError" class="rounded-[22px] border border-rose-200 bg-rose-50 px-4 py-5 text-sm text-rose-900">
                  <p class="font-medium">会话列表加载失败</p>
                  <p class="mt-1 text-rose-800/80">{{ listErrorMessage }}</p>
                  <Button variant="outline" size="sm" class="mt-3 rounded-full border-rose-200 bg-white text-rose-700" @click="refetchList()">
                    重试
                  </Button>
                </div>

                <div v-else-if="!sessionCards.length" class="rounded-[22px] border border-dashed border-stone-300 bg-stone-50/70 px-4 py-10 text-center text-sm text-stone-500">
                  当前筛选条件下没有命中会话。
                </div>

                <div v-else class="space-y-3">
                  <div
                    v-for="item in sessionCards"
                    :key="item.sessionId"
                    role="button"
                    tabindex="0"
                    class="w-full rounded-[24px] border p-4 text-left transition-all"
                    :class="selectedSessionId === item.sessionId
                      ? 'border-stone-900 bg-stone-950 text-stone-50 shadow-[0_20px_40px_rgba(41,37,36,0.16)]'
                      : 'border-stone-200 bg-stone-50/80 text-stone-900 hover:border-stone-300 hover:bg-white'"
                    @click="dashboardStore.setSelectedSessionId(item.sessionId)"
                    @keydown.enter.prevent="dashboardStore.setSelectedSessionId(item.sessionId)"
                    @keydown.space.prevent="dashboardStore.setSelectedSessionId(item.sessionId)"
                  >
                    <div class="flex items-start justify-between gap-3">
                      <div class="min-w-0">
                        <p class="truncate text-sm font-semibold">{{ item.storyTitle }}</p>
                        <p v-if="item.worldId" class="mt-1 text-xs opacity-70">世界：{{ resolveWorldDisplay(item.worldId) }}</p>
                        <p class="mt-3 text-xs opacity-80">最近变化：{{ item.latestEventHeadline }}</p>
                        <p class="mt-1 text-xs leading-5 opacity-70">
                          {{ getExpandableText(`session-reason-${item.sessionId}`, item.latestReason, 68) }}
                        </p>
                        <button
                          v-if="isTextTruncated(item.latestReason, 68)"
                          type="button"
                          class="mt-1 text-[11px] font-medium opacity-80 underline-offset-4 hover:underline"
                          @click.stop="toggleTextExpansion(`session-reason-${item.sessionId}`)"
                        >
                          {{ isTextExpanded(`session-reason-${item.sessionId}`) ? '收起' : '展开' }}
                        </button>
                      </div>

                      <div class="flex shrink-0 flex-col items-end gap-2">
                        <Badge class="border text-[10px]" :class="item.summaryDescriptor.badgeTone">
                          {{ item.summaryDescriptor.label }}
                        </Badge>
                        <Badge v-if="item.hasFailed" class="border text-[10px]" :class="statusBadgeClass('failed')">
                          需要处理
                        </Badge>
                      </div>
                    </div>

                    <div class="mt-4 grid grid-cols-3 gap-2 text-[11px]">
                      <div class="rounded-2xl border border-current/10 px-3 py-2">
                        <p class="opacity-60">变动</p>
                        <p class="mt-1 font-semibold">{{ item.eventCount }}</p>
                      </div>
                      <div class="rounded-2xl border border-current/10 px-3 py-2">
                        <p class="opacity-60">摘要</p>
                        <p class="mt-1 font-semibold">{{ item.semanticCount }}</p>
                      </div>
                      <div class="rounded-2xl border border-current/10 px-3 py-2">
                        <p class="opacity-60">角色</p>
                        <p class="mt-1 font-semibold">{{ item.trackedEntities }}</p>
                      </div>
                    </div>

                    <p class="mt-3 text-[11px] opacity-60">{{ formatTimestamp(item.latestEvent?.committed_at) }}</p>
                  </div>
                </div>
              </CardContent>
            </Card>
          </aside>

          <main class="space-y-5">
            <section
              v-if="selectedSessionCard"
              class="rounded-[30px] border border-border bg-background p-6 shadow-sm"
            >
              <div class="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
                <div class="max-w-3xl">
                  <div class="flex flex-wrap items-center gap-2">
                    <Badge class="border text-[10px]" :class="selectedSessionCard.summaryDescriptor.badgeTone">
                      {{ selectedSessionCard.summaryDescriptor.label }}
                    </Badge>
                    <Badge class="border text-[10px]" :class="statusBadgeClass(selectedStoryMemory?.operation?.status ?? latestTimelineEvent?.status)">
                      {{ getMemoryStatusLabel(selectedStoryMemory?.operation?.status ?? latestTimelineEvent?.status) }}
                    </Badge>
                    <Badge
                      v-if="selectedStoryMemory?.operation?.source || latestTimelineEvent?.source"
                      variant="secondary"
                      class="text-[10px]"
                    >
                      {{ getMemorySourceLabel(selectedStoryMemory?.operation?.source ?? latestTimelineEvent?.source ?? '') }}
                    </Badge>
                  </div>

                  <h2 class="hero-title mt-4 text-3xl text-stone-950">{{ selectedSessionCard.storyTitle }}</h2>
                  <p class="mt-2 text-sm leading-6 text-stone-700">
                    {{ detailSummaryDescriptor.description }}
                  </p>

                  <div class="mt-4 flex flex-wrap gap-x-4 gap-y-2 text-xs text-stone-500">
                    <span>会话：{{ selectedSessionCard.sessionId }}</span>
                    <span v-if="selectedSessionCard.worldId">世界：{{ resolveWorldDisplay(selectedSessionCard.worldId) }}</span>
                    <span>最近更新时间：{{ formatTimestamp(latestTimelineEvent?.committed_at) }}</span>
                  </div>
                </div>

                <div class="grid w-full gap-3 sm:grid-cols-2 xl:w-[420px]">
                  <div class="rounded-[22px] border border-white/80 bg-white/82 px-4 py-4">
                    <p class="text-[11px] uppercase tracking-[0.22em] text-stone-500">摘要状态</p>
                    <p class="mt-2 text-sm font-semibold text-stone-950">{{ detailSummaryDescriptor.label }}</p>
                  </div>
                  <div class="rounded-[22px] border border-white/80 bg-white/82 px-4 py-4">
                    <p class="text-[11px] uppercase tracking-[0.22em] text-stone-500">当前角色数</p>
                    <p class="mt-2 text-sm font-semibold text-stone-950">{{ selectedEntitySnapshot?.total ?? 0 }} 人</p>
                  </div>
                  <div class="rounded-[22px] border border-white/80 bg-white/82 px-4 py-4">
                    <p class="text-[11px] uppercase tracking-[0.22em] text-stone-500">历史总条数</p>
                    <p class="mt-2 text-sm font-semibold text-stone-950">{{ detailTotal }}</p>
                  </div>
                  <div class="rounded-[22px] border border-white/80 bg-white/82 px-4 py-4">
                    <p class="text-[11px] uppercase tracking-[0.22em] text-stone-500">已覆盖地点</p>
                    <p class="mt-2 text-sm font-semibold text-stone-950">{{ selectedEntityLocationCount }}</p>
                  </div>
                </div>
              </div>

              <div v-if="failedEvents.length" class="mt-5 rounded-[24px] border border-rose-200 bg-rose-50/90 px-4 py-4 text-sm text-rose-900">
                <div class="flex items-center gap-2">
                  <AlertTriangle class="h-4 w-4" />
                  <p class="font-semibold">当前会话仍有失败事件</p>
                </div>
                <p class="mt-2 leading-6 text-rose-800/90">
                  {{ failedEvents.map((event) => event.title).join('；') }}
                </p>
              </div>
            </section>

            <div v-else class="rounded-[30px] border border-dashed border-stone-300 bg-white/80 px-6 py-14 text-center text-sm text-stone-500">
              请选择左侧会话查看故事记忆详情。
            </div>

            <template v-if="selectedSessionCard">
              <section class="grid gap-5 2xl:grid-cols-[minmax(0,1.15fr)_minmax(320px,0.85fr)]">
                <Card class="rounded-[28px] border-stone-200/80 bg-white/90 shadow-none">
                  <CardHeader>
                    <CardTitle class="flex items-center gap-2 text-stone-950">
                      <ArrowLeftRight class="h-4 w-4 text-stone-600" />
                      本轮变化
                    </CardTitle>
                    <CardDescription>用实体与摘要两条线，把最近变化翻译成自然语言。</CardDescription>
                  </CardHeader>
                  <CardContent class="space-y-4">
                    <div v-if="!recentEntityChangeGroups.length" class="rounded-[22px] border border-dashed border-stone-300 bg-stone-50/70 px-4 py-10 text-center text-sm text-stone-500">
                      当前还没有可读的实体变化摘要。
                    </div>

                    <article
                      v-for="group in recentEntityChangeGroups"
                      :key="group.id"
                      class="rounded-[24px] border border-stone-200 bg-stone-50/80 p-4"
                    >
                      <div class="flex items-start justify-between gap-3">
                        <div>
                          <p class="text-[11px] uppercase tracking-[0.22em] text-stone-500">实体</p>
                          <p class="mt-1 text-lg font-semibold text-stone-950">{{ group.entityLabel }}</p>
                        </div>
                        <Badge variant="secondary" class="text-[10px]">
                          {{ formatTimestamp(group.committedAt) }}
                        </Badge>
                      </div>

                      <div class="mt-4 space-y-2">
                        <article
                          v-for="change in group.changes.slice(0, 3)"
                          :key="change.id"
                          class="rounded-2xl border border-white/90 bg-white/85 p-3"
                        >
                          <p class="text-sm font-medium text-stone-900">变化：{{ change.summary }}</p>
                          <div class="mt-3 grid gap-3 lg:grid-cols-2">
                            <div class="rounded-2xl border border-stone-200 bg-stone-50/80 px-3 py-3">
                              <p class="text-[11px] uppercase tracking-[0.22em] text-stone-500">变更前</p>
                              <p class="mt-2 text-xs font-medium text-stone-600">{{ change.fieldLabel }}</p>
                              <p class="mt-2 text-sm leading-6 text-stone-800">
                                {{ getExpandableText(`group-before-${change.id}`, change.beforeText, 64) }}
                              </p>
                              <button
                                v-if="isTextTruncated(change.beforeText, 64)"
                                type="button"
                                class="mt-1 text-[11px] font-medium text-stone-500 underline-offset-4 hover:underline"
                                @click="toggleTextExpansion(`group-before-${change.id}`)"
                              >
                                {{ isTextExpanded(`group-before-${change.id}`) ? '收起' : '展开' }}
                              </button>
                            </div>
                            <div class="rounded-2xl border border-emerald-200 bg-emerald-50/70 px-3 py-3">
                              <p class="text-[11px] uppercase tracking-[0.22em] text-emerald-700">变更后</p>
                              <p class="mt-2 text-xs font-medium text-emerald-700">{{ change.fieldLabel }}</p>
                              <p class="mt-2 text-sm leading-6 text-stone-800">
                                {{ getExpandableText(`group-after-${change.id}`, change.afterText, 64) }}
                              </p>
                              <button
                                v-if="isTextTruncated(change.afterText, 64)"
                                type="button"
                                class="mt-1 text-[11px] font-medium text-emerald-700 underline-offset-4 hover:underline"
                                @click="toggleTextExpansion(`group-after-${change.id}`)"
                              >
                                {{ isTextExpanded(`group-after-${change.id}`) ? '收起' : '展开' }}
                              </button>
                            </div>
                          </div>
                        </article>
                        <p v-if="group.changes.length > 3" class="text-xs text-stone-500">
                          还有 {{ group.changes.length - 3 }} 条变化未展开。
                        </p>
                      </div>

                      <p v-if="group.evidence[0]" class="mt-4 text-xs leading-5 text-stone-600">
                        证据：{{ getExpandableText(`group-evidence-${group.id}`, group.evidence[0], 96) }}
                      </p>
                      <button
                        v-if="group.evidence[0] && isTextTruncated(group.evidence[0], 96)"
                        type="button"
                        class="mt-1 text-[11px] font-medium text-stone-500 underline-offset-4 hover:underline"
                        @click="toggleTextExpansion(`group-evidence-${group.id}`)"
                      >
                        {{ isTextExpanded(`group-evidence-${group.id}`) ? '收起' : '展开' }}
                      </button>
                      <p v-if="group.sourceTurn" class="mt-2 text-[11px] text-stone-500">
                        来源轮次：第 {{ group.sourceTurn }} 轮
                      </p>
                    </article>
                  </CardContent>
                </Card>

                <div class="space-y-5">
                  <Card class="rounded-[28px] border-violet-200/80 bg-[linear-gradient(180deg,rgba(245,243,255,0.98),rgba(255,255,255,0.92))] shadow-none">
                    <CardHeader>
                      <CardTitle class="flex items-center gap-2 text-violet-950">
                        <Brain class="h-4 w-4 text-violet-700" />
                        当前摘要
                      </CardTitle>
                      <CardDescription>优先展示可继续用于生成的语义摘要。</CardDescription>
                    </CardHeader>
                    <CardContent class="space-y-4">
                      <div v-if="selectedSummarySnapshot" class="rounded-[22px] border border-white/90 bg-white/85 px-4 py-4 text-sm leading-7 text-stone-800">
                        {{ selectedSummarySnapshot.summary_text }}
                      </div>
                      <div v-else class="rounded-[22px] border border-dashed border-violet-200 bg-white/80 px-4 py-8 text-center text-sm text-violet-900/70">
                        当前没有可用摘要。
                      </div>

                      <div v-if="selectedSummarySnapshot?.key_facts?.length" class="flex flex-wrap gap-2">
                        <Badge
                          v-for="fact in selectedSummarySnapshot.key_facts.slice(0, 8)"
                          :key="fact"
                          class="border border-violet-200 bg-white/90 text-[11px] font-normal text-violet-900"
                        >
                          {{ fact }}
                        </Badge>
                      </div>

                      <div v-if="latestSemanticEvent" class="rounded-[22px] border border-violet-200/70 bg-white/80 px-4 py-4">
                        <p class="text-[11px] uppercase tracking-[0.22em] text-violet-700">最近摘要动作</p>
                        <p class="mt-2 text-sm font-semibold text-stone-950">{{ buildEventHeadline(latestSemanticEvent) }}</p>
                        <p class="mt-2 text-xs leading-5 text-stone-600">
                          {{ latestSemanticEvent.reason || latestSemanticEvent.title }}
                        </p>
                      </div>
                    </CardContent>
                  </Card>

                  <Card class="rounded-[28px] border-stone-200/80 bg-white/90 shadow-none">
                    <CardHeader>
                      <CardTitle class="flex items-center gap-2 text-stone-950">
                        <MapPinned class="h-4 w-4 text-stone-600" />
                        提醒与世界变化
                      </CardTitle>
                      <CardDescription>这里放当前会话最适合人工快速确认的信息。</CardDescription>
                    </CardHeader>
                    <CardContent class="space-y-3">
                      <div v-if="selectedWorldUpdateHighlights.length" class="space-y-2">
                        <p
                          v-for="line in selectedWorldUpdateHighlights"
                          :key="line"
                          class="rounded-2xl border border-stone-200 bg-stone-50/70 px-3 py-2 text-sm leading-6 text-stone-800"
                        >
                          {{ line }}
                        </p>
                      </div>
                      <div v-else class="rounded-2xl border border-dashed border-stone-300 bg-stone-50/70 px-4 py-6 text-sm text-stone-500">
                        当前没有结构化 world update。
                      </div>

                      <div class="space-y-2">
                        <p
                          v-for="warning in selectedEntityWarnings"
                          :key="warning"
                          class="rounded-2xl border border-stone-200 bg-white px-3 py-2 text-sm leading-6 text-stone-700"
                        >
                          {{ warning }}
                        </p>
                      </div>
                    </CardContent>
                  </Card>
                </div>
              </section>

              <Card class="rounded-[28px] border-stone-200/80 bg-white/90 shadow-none">
                <CardHeader>
                  <CardTitle class="flex items-center gap-2 text-stone-950">
                    <Users class="h-4 w-4 text-stone-600" />
                    当前角色状态
                  </CardTitle>
                  <CardDescription>一张卡只表达一个角色当前的关键信息，避免把字段级结构直接抛给人看。</CardDescription>
                </CardHeader>
                <CardContent>
                  <div v-if="selectedEntitySnapshot?.items?.length" class="grid gap-4 md:grid-cols-2 2xl:grid-cols-3">
                    <article
                      v-for="entity in selectedEntitySnapshot.items"
                      :key="entity.entity_id"
                      class="rounded-[24px] border border-stone-200 bg-stone-50/80 p-4"
                    >
                      <div class="flex items-start justify-between gap-3">
                        <div class="min-w-0">
                          <p class="truncate text-base font-semibold text-stone-950">{{ entity.display_name }}</p>
                          <p class="mt-1 text-xs text-stone-500">
                            {{ entity.current_location || '位置待确认' }}
                          </p>
                        </div>
                        <Badge variant="secondary" class="text-[10px]">
                          {{ formatTimestamp(entity.updated_at) }}
                        </Badge>
                      </div>

                      <p class="mt-4 rounded-2xl border border-white/90 bg-white/85 px-3 py-3 text-sm leading-6 text-stone-800">
                        {{ entity.state_summary || '当前还没有压缩后的角色摘要。' }}
                      </p>

                      <div v-if="entity.status_tags.length" class="mt-3 flex flex-wrap gap-2">
                        <Badge
                          v-for="tag in entity.status_tags"
                          :key="`${entity.entity_id}-${tag}`"
                          class="border border-stone-200 bg-white text-[11px] font-normal text-stone-800"
                        >
                          {{ tag }}
                        </Badge>
                      </div>

                      <div v-if="entity.inventory.length" class="mt-4 flex items-start gap-2 text-sm text-stone-700">
                        <Package class="mt-0.5 h-4 w-4 shrink-0 text-stone-500" />
                        <span class="leading-6">{{ entity.inventory.join('、') }}</span>
                      </div>

                      <div v-if="entity.companions.length" class="mt-3 flex items-start gap-2 text-sm text-stone-700">
                        <Users class="mt-0.5 h-4 w-4 shrink-0 text-stone-500" />
                        <span class="leading-6">{{ entity.companions.map((item) => resolveEntityCompanionLabel(item)).join('、') }}</span>
                      </div>

                      <div v-if="entity.evidence.length" class="mt-4 rounded-2xl border border-stone-200 bg-white/90 px-3 py-3">
                        <p class="text-[11px] uppercase tracking-[0.22em] text-stone-500">最近证据</p>
                        <p class="mt-2 text-sm leading-6 text-stone-700">
                          {{ getExpandableText(`entity-evidence-${entity.entity_id}`, entity.evidence[0] ?? '', 120) }}
                        </p>
                        <button
                          v-if="entity.evidence[0] && isTextTruncated(entity.evidence[0], 120)"
                          type="button"
                          class="mt-1 text-[11px] font-medium text-stone-500 underline-offset-4 hover:underline"
                          @click="toggleTextExpansion(`entity-evidence-${entity.entity_id}`)"
                        >
                          {{ isTextExpanded(`entity-evidence-${entity.entity_id}`) ? '收起' : '展开' }}
                        </button>
                      </div>
                    </article>
                  </div>

                  <div v-else class="rounded-[22px] border border-dashed border-stone-300 bg-stone-50/70 px-4 py-10 text-center text-sm text-stone-500">
                    当前会话还没有实体状态快照。
                  </div>
                </CardContent>
              </Card>

              <Card class="rounded-[28px] border-stone-200/80 bg-white/90 shadow-none">
                <CardHeader class="gap-4">
                  <div class="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
                    <div>
                      <CardTitle class="flex items-center gap-2 text-stone-950">
                        <CalendarRange class="h-4 w-4 text-stone-600" />
                        历史记录
                      </CardTitle>
                      <CardDescription>按页回看记忆事件，重点展示“发生了什么”和“现在留下了什么”。</CardDescription>
                    </div>

                    <div class="flex flex-wrap items-center gap-2">
                      <Select
                        :model-value="String(detailPageSize)"
                        @update:model-value="(value) => dashboardStore.setDetailPageSize(Number(value))"
                      >
                        <SelectTrigger class="h-9 w-[110px] rounded-full border-stone-200 bg-stone-50/70 text-xs">
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem v-for="option in pageSizeOptions" :key="option.value" :value="option.value">
                            {{ option.label }}
                          </SelectItem>
                        </SelectContent>
                      </Select>

                      <Button
                        variant="outline"
                        size="sm"
                        class="rounded-full border-stone-200 bg-white"
                        :disabled="detailPage <= 1"
                        @click="goToPreviousPage"
                      >
                        <ChevronLeft class="h-4 w-4" />
                        上一页
                      </Button>
                      <Button
                        variant="outline"
                        size="sm"
                        class="rounded-full border-stone-200 bg-white"
                        :disabled="detailPage >= detailPageCount"
                        @click="goToNextPage"
                      >
                        下一页
                        <ChevronRight class="h-4 w-4" />
                      </Button>
                    </div>
                  </div>

                  <div class="flex flex-wrap items-center gap-x-4 gap-y-2 text-xs text-stone-500">
                    <span>{{ historyRangeLabel }}</span>
                    <span>当前第 {{ detailPage }} / {{ detailPageCount }} 页</span>
                    <span v-if="timelineFetching || storyMemoryFetching">正在刷新当前页…</span>
                  </div>
                </CardHeader>

                <CardContent class="space-y-4">
                  <div v-if="timelineLoading && !effectiveTimelineResponse" class="rounded-[22px] border border-dashed border-stone-300 bg-stone-50/70 px-4 py-10 text-center text-sm text-stone-500">
                    正在加载历史记录…
                  </div>

                  <div v-else-if="timelineError" class="rounded-[22px] border border-rose-200 bg-rose-50 px-4 py-5 text-sm text-rose-900">
                    <p class="font-medium">历史记录加载失败</p>
                    <p class="mt-1 text-rose-800/80">{{ timelineErrorMessage }}</p>
                    <Button variant="outline" size="sm" class="mt-3 rounded-full border-rose-200 bg-white text-rose-700" @click="refetchTimeline()">
                      重试
                    </Button>
                  </div>

                  <div v-else-if="!operationGroups.length" class="rounded-[22px] border border-dashed border-stone-300 bg-stone-50/70 px-4 py-10 text-center text-sm text-stone-500">
                    当前页没有历史记录。
                  </div>

                  <article
                    v-for="group in operationGroups"
                    :key="group.id"
                    class="rounded-[26px] border border-stone-200 bg-stone-50/80 p-4"
                  >
                    <div class="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
                      <div>
                        <div class="flex flex-wrap items-center gap-2">
                          <Badge variant="secondary" class="text-[10px]">{{ group.label }}</Badge>
                          <Badge class="border text-[10px]" :class="statusBadgeClass(group.status)">
                            {{ getMemoryStatusLabel(group.status) }}
                          </Badge>
                          <Badge
                            v-if="group.semanticState !== 'absent'"
                            class="border text-[10px]"
                            :class="getSummaryLifecycleDescriptor(group.semanticState).badgeTone"
                          >
                            {{ getSummaryLifecycleDescriptor(group.semanticState).label }}
                          </Badge>
                        </div>

                        <p class="mt-3 text-base font-semibold text-stone-950">{{ summarizeOperation(group.events) }}</p>
                        <p class="mt-2 text-sm leading-6 text-stone-600">
                          {{ formatTimestamp(group.startedAt) }}
                          <span v-if="group.startedAt !== group.endedAt"> 至 {{ formatTimestamp(group.endedAt) }}</span>
                        </p>
                      </div>

                      <div class="rounded-[22px] border border-white/90 bg-white/85 px-4 py-3 text-sm text-stone-700">
                        本批次共 {{ group.events.length }} 条事件
                      </div>
                    </div>

                    <div class="mt-4 space-y-3">
                      <article
                        v-for="event in group.events"
                        :key="event.event_id"
                        class="rounded-[22px] border border-white/90 bg-white/92 p-4"
                      >
                        <div class="flex flex-wrap items-center gap-2">
                          <Badge class="border text-[10px]" :class="layerBadgeClass(event.memory_layer)">
                            {{ getMemoryLayerLabel(event.memory_layer) }}
                          </Badge>
                          <Badge class="border text-[10px]" :class="statusBadgeClass(event.status)">
                            {{ getMemoryStatusLabel(event.status) }}
                          </Badge>
                          <Badge v-if="event.display_kind" variant="secondary" class="text-[10px]">
                            {{ event.display_kind }}
                          </Badge>
                        </div>

                        <p class="mt-3 text-sm font-semibold text-stone-950">{{ buildEventHeadline(event) }}</p>
                        <p class="mt-1 text-sm leading-6 text-stone-700">{{ event.reason || event.title }}</p>

                        <div class="mt-3 flex flex-wrap gap-x-4 gap-y-2 text-[11px] text-stone-500">
                          <span>{{ getMemorySourceLabel(event.source) }}</span>
                          <span v-if="event.source_turn">第 {{ event.source_turn }} 轮</span>
                          <span>{{ formatTimestamp(event.committed_at) }}</span>
                        </div>

                        <div v-if="previewPayloadFields(event.after).length || previewPayloadFields(event.before).length" class="mt-4 grid gap-3 lg:grid-cols-2">
                          <div v-if="previewPayloadFields(event.before).length" class="rounded-2xl border border-stone-200 bg-stone-50/80 px-3 py-3">
                            <p class="text-[11px] uppercase tracking-[0.22em] text-stone-500">变更前</p>
                            <p
                              v-for="field in previewPayloadFields(event.before)"
                              :key="`before-${event.event_id}-${field.label}`"
                              class="mt-2 text-sm leading-6 text-stone-700"
                            >
                              <span class="font-medium text-stone-500">{{ field.label }}：</span>{{ getExpandableText(`timeline-before-${event.event_id}-${field.label}`, field.value, field.label === '摘要' ? 140 : 72) }}
                            </p>
                            <button
                              v-for="field in previewPayloadFields(event.before).filter((item) => isTextTruncated(item.value, item.label === '摘要' ? 140 : 72))"
                              :key="`before-toggle-${event.event_id}-${field.label}`"
                              type="button"
                              class="block text-[11px] font-medium text-stone-500 underline-offset-4 hover:underline"
                              @click="toggleTextExpansion(`timeline-before-${event.event_id}-${field.label}`)"
                            >
                              {{ isTextExpanded(`timeline-before-${event.event_id}-${field.label}`) ? `收起${field.label}` : `展开${field.label}` }}
                            </button>
                          </div>
                          <div v-if="previewPayloadFields(event.after).length" class="rounded-2xl border border-stone-200 bg-stone-50/80 px-3 py-3">
                            <p class="text-[11px] uppercase tracking-[0.22em] text-stone-500">变更后</p>
                            <p
                              v-for="field in previewPayloadFields(event.after)"
                              :key="`after-${event.event_id}-${field.label}`"
                              class="mt-2 text-sm leading-6 text-stone-700"
                            >
                              <span class="font-medium text-stone-500">{{ field.label }}：</span>{{ getExpandableText(`timeline-after-${event.event_id}-${field.label}`, field.value, field.label === '摘要' ? 140 : 72) }}
                            </p>
                            <button
                              v-for="field in previewPayloadFields(event.after).filter((item) => isTextTruncated(item.value, item.label === '摘要' ? 140 : 72))"
                              :key="`after-toggle-${event.event_id}-${field.label}`"
                              type="button"
                              class="block text-[11px] font-medium text-stone-500 underline-offset-4 hover:underline"
                              @click="toggleTextExpansion(`timeline-after-${event.event_id}-${field.label}`)"
                            >
                              {{ isTextExpanded(`timeline-after-${event.event_id}-${field.label}`) ? `收起${field.label}` : `展开${field.label}` }}
                            </button>
                          </div>
                        </div>
                      </article>
                    </div>
                  </article>
                </CardContent>
              </Card>

              <Card v-if="selectedEntityPatchUpdates.length" class="rounded-[28px] border-stone-200/80 bg-white/90 shadow-none">
                <CardHeader>
                  <CardTitle class="flex items-center gap-2 text-stone-950">
                    <UserRound class="h-4 w-4 text-stone-600" />
                    最近字段级变化
                  </CardTitle>
                  <CardDescription>保留字段级 patch 视角，但只显示易读名称，不再把复杂 id 当主标识。</CardDescription>
                </CardHeader>
                <CardContent class="grid gap-3 lg:grid-cols-2">
                  <article
                    v-for="patch in selectedEntityPatchUpdates.slice(0, 12)"
                    :key="getEntityPatchEventId(patch)"
                    class="rounded-[22px] border border-stone-200 bg-stone-50/80 p-4"
                  >
                    <div class="flex items-start justify-between gap-3">
                      <div>
                        <p class="text-[11px] uppercase tracking-[0.22em] text-stone-500">实体</p>
                        <p class="mt-1 text-sm font-semibold text-stone-950">{{ getEntityPatchEntityLabel(patch) }}</p>
                      </div>
                      <Badge class="border text-[10px]" :class="statusBadgeClass(patch.status)">
                        {{ getMemoryStatusLabel(patch.status) }}
                      </Badge>
                    </div>

                    <p class="mt-4 text-sm leading-6 text-stone-800">
                      变化：{{ getEntityPatchChangeSummary(patch) }}
                    </p>
                    <p class="mt-2 text-xs text-stone-500">
                      字段：{{ getEntityPatchFieldLabel(patch) }} · {{ formatTimestamp(getEntityPatchCommittedAt(patch)) }}
                    </p>
                    <div class="mt-3 grid gap-3 sm:grid-cols-2">
                      <div class="rounded-2xl border border-stone-200 bg-white/85 px-3 py-3">
                        <p class="text-[11px] uppercase tracking-[0.22em] text-stone-500">变更前</p>
                        <p class="mt-2 text-sm leading-6 text-stone-800">
                          {{ getExpandableText(`patch-before-${getEntityPatchEventId(patch)}`, formatEntityPatchValue(patch.before ?? (patch.op === 'remove' ? patch.value : null)), 72) }}
                        </p>
                        <button
                          v-if="isTextTruncated(formatEntityPatchValue(patch.before ?? (patch.op === 'remove' ? patch.value : null)), 72)"
                          type="button"
                          class="mt-1 text-[11px] font-medium text-stone-500 underline-offset-4 hover:underline"
                          @click="toggleTextExpansion(`patch-before-${getEntityPatchEventId(patch)}`)"
                        >
                          {{ isTextExpanded(`patch-before-${getEntityPatchEventId(patch)}`) ? '收起' : '展开' }}
                        </button>
                      </div>
                      <div class="rounded-2xl border border-emerald-200 bg-emerald-50/70 px-3 py-3">
                        <p class="text-[11px] uppercase tracking-[0.22em] text-emerald-700">变更后</p>
                        <p class="mt-2 text-sm leading-6 text-stone-800">
                          {{ getExpandableText(`patch-after-${getEntityPatchEventId(patch)}`, formatEntityPatchValue(patch.after ?? (patch.op !== 'remove' ? patch.value : null)), 72) }}
                        </p>
                        <button
                          v-if="isTextTruncated(formatEntityPatchValue(patch.after ?? (patch.op !== 'remove' ? patch.value : null)), 72)"
                          type="button"
                          class="mt-1 text-[11px] font-medium text-emerald-700 underline-offset-4 hover:underline"
                          @click="toggleTextExpansion(`patch-after-${getEntityPatchEventId(patch)}`)"
                        >
                          {{ isTextExpanded(`patch-after-${getEntityPatchEventId(patch)}`) ? '收起' : '展开' }}
                        </button>
                      </div>
                    </div>
                    <p v-if="getEntityPatchEvidenceText(patch)" class="mt-2 text-xs leading-5 text-stone-600">
                      证据：{{ getExpandableText(`patch-evidence-${getEntityPatchEventId(patch)}`, getEntityPatchEvidenceText(patch) ?? '', 96) }}
                    </p>
                    <button
                      v-if="getEntityPatchEvidenceText(patch) && isTextTruncated(getEntityPatchEvidenceText(patch) ?? '', 96)"
                      type="button"
                      class="mt-1 text-[11px] font-medium text-stone-500 underline-offset-4 hover:underline"
                      @click="toggleTextExpansion(`patch-evidence-${getEntityPatchEventId(patch)}`)"
                    >
                      {{ isTextExpanded(`patch-evidence-${getEntityPatchEventId(patch)}`) ? '收起' : '展开' }}
                    </button>
                  </article>
                </CardContent>
              </Card>
            </template>
          </main>
        </div>
      </section>
    </div>
  </div>
</template>

<style scoped>
.memory-stat {
  background: rgba(255, 255, 255, 0.78);
}

.hero-title {
  font-family: "Noto Serif SC", "Source Han Serif SC", "Songti SC", "STSong", serif;
  letter-spacing: -0.02em;
}
</style>
