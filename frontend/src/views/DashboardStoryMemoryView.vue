<script setup lang="ts">
// 文件说明：前端页面级视图编排。
import { storeToRefs } from 'pinia'
import { computed, ref, watch } from 'vue'
import {
  AlertTriangle,
  Brain,
  CalendarRange,
  ChevronLeft,
  ChevronRight,
  MapPinned,
  Package,
  RefreshCw,
  Search,
  UserRound,
  Users,
} from 'lucide-vue-next'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import {
  useMemoryUpdatesQuery,
  useSessionMemoryTimelineQuery,
  useSessionStoryMemoryQuery,
} from '@/domains/memory/queries/useMemoryUpdateQueries'
import { useLorebookEntriesQuery, useWorldsQuery } from '@/domains/lorebook/queries/useLorebookQueries'
import type { MemoryUpdateTimelineItem } from '@/domains/memory/api/memoryUpdatesApi'
import {
  deriveSummaryLifecycleState,
  formatMemoryPayloadFields,
  getMemoryActionLabel,
  getMemoryLayerLabel,
  getMemorySourceLabel,
  getMemoryStatusLabel,
  getSummaryLifecycleDescriptor,
  type MemoryPayloadField,
  type SummaryLifecycleState,
} from '@/domains/memory/memoryUpdatePresentation'
import {
  buildStoryMemoryRounds,
  type StoryMemoryRoundView,
} from '@/domains/memory/storyMemoryRounds'
import {
  buildEntityNameMap,
  extractWorldUpdateHighlights,
  getEntityPatchChangeSummary,
  getEntityPatchCommittedAt,
  getEntityPatchEntityLabel,
  getEntityPatchEvidenceText,
  getEntityPatchEventId,
  getEntityPatchFieldLabel,
  getEntityPatchFieldName,
} from '@/domains/story/entityPatchPresentation'
import {
  getEntityCompanionDisplayName,
  getEntityCompanionId,
  getEntityCompanionLabel,
} from '@/domains/story/entityCompanion'
import {
  getStoryMemoryEntitySnapshot,
  getStoryMemoryEntityUpdates,
  getStoryMemorySummarySnapshot,
  getStoryMemoryTimelineEvents,
  getStoryMemoryWorldUpdate,
} from '@/domains/story/storyMemoryPayload'
import { useStoryQuery } from '@/domains/story/queries/useStoryQueries'
import { useMemoryUpdateDashboardStore } from '@/stores/memoryUpdateDashboard'
import { useStorySessionStore } from '@/stores/storySession'

// 故事会话与记忆快照仓库。
const storySessionStore = useStorySessionStore()
// 记忆看板筛选与分页状态仓库。
const dashboardStore = useMemoryUpdateDashboardStore()

const {
  sessionSearchTerm,
  selectedSessionId,
  detailPage,
  listSnapshot,
  queryFilters,
} = storeToRefs(dashboardStore)

dashboardStore.setSearchTerm('')
dashboardStore.setSelectedSource('all')
dashboardStore.setSelectedLayer('all')
dashboardStore.setSelectedStatus('all')
dashboardStore.setSessionViewMode('all')

const TIMELINE_FETCH_PAGE_SIZE = 200

// 可展开文本的展开状态记录。
const expandedTextState = ref<Record<string, boolean>>({})

// 本地缓存的会话摘要列表。
const summaries = computed(() => storySessionStore.getAllSummaries())
// 按 sessionId 索引的摘要映射。
const summaryMap = computed(() => new Map(summaries.value.map((record) => [record.sessionId, record])))
// 按 sessionId 索引的 story memory 映射。
const storyMemorySessionMap = computed(() => new Map(
  storySessionStore.getAllStoryMemorySessions().map((record) => [record.sessionId, record]),
))
const { data: worlds } = useWorldsQuery()
// 世界 ID 到名称的映射。
const worldNameMap = computed(() => new Map((worlds.value ?? []).map((world) => [world.id, world.name])))

const {
  data: listResponse,
  isLoading: listLoading,
  isFetching: listFetching,
  error: listError,
  refetch: refetchList,
} = useMemoryUpdatesQuery(queryFilters)

// 会话列表加载失败提示文案。
const listErrorMessage = computed(() => (
  listError.value instanceof Error ? listError.value.message : '无法获取服务端记忆事件列表。'
))
// 会话列表的有效数据源（优先远端，回退快照）。
const effectiveListResponse = computed(() => listResponse.value ?? listSnapshot.value ?? null)

/** 推导会话卡片的摘要生命周期状态。*/
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

/** 生成事件卡片标题。*/
function buildEventHeadline(event: Pick<MemoryUpdateTimelineItem, 'memory_layer' | 'action'>) {
  return `${getMemoryLayerLabel(event.memory_layer)}：${getMemoryActionLabel(event.action)}`
}

/** 裁剪长文本并保留省略号。*/
function compactText(value: string, maxLength = 88) {
  const normalized = value.trim()
  return normalized.length > maxLength ? `${normalized.slice(0, maxLength - 1)}…` : normalized
}

/** 判断文本是否超过展示长度。*/
function isTextTruncated(value: string, maxLength = 88) {
  return value.trim().length > maxLength
}

/** 读取指定文本块的展开状态。*/
function isTextExpanded(key: string) {
  return Boolean(expandedTextState.value[key])
}

/** 切换指定文本块的展开状态。*/
function toggleTextExpansion(key: string) {
  expandedTextState.value = {
    ...expandedTextState.value,
    [key]: !expandedTextState.value[key],
  }
}

/** 按展开状态返回文本或摘要。*/
function getExpandableText(key: string, value: string, maxLength = 88) {
  const normalized = value.trim()
  if (!normalized) return ''
  if (isTextExpanded(key) || !isTextTruncated(normalized, maxLength)) return normalized
  return compactText(normalized, maxLength)
}

/** 解析世界显示名（名称 + ID）。*/
function resolveWorldDisplay(worldId?: string | null) {
  const normalizedWorldId = (worldId ?? '').trim()
  if (!normalizedWorldId) return '未绑定世界'
  const worldName = worldNameMap.value.get(normalizedWorldId)
  if (!worldName) return normalizedWorldId
  return `${worldName} · ${normalizedWorldId}`
}

/** 格式化时间戳为本地展示时间。*/
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

/** 按状态返回徽标样式类名。*/
function statusBadgeClass(status?: string | null) {
  if (status === 'failed') return 'border-rose-200 bg-rose-50 text-rose-700'
  if (status === 'stale') return 'border-amber-200 bg-amber-50 text-amber-700'
  return 'border-emerald-200 bg-emerald-50 text-emerald-700'
}

/** 按记忆层级返回徽标样式类名。*/
function layerBadgeClass(layer: string) {
  if (layer === 'semantic') return 'border-violet-200 bg-violet-50 text-violet-700'
  if (layer === 'episodic') return 'border-sky-200 bg-sky-50 text-sky-700'
  if (layer === 'entity_state') return 'border-orange-200 bg-orange-50 text-orange-700'
  return 'border-stone-200 bg-stone-50 text-stone-700'
}

/** 提取 payload 预览字段。*/
function previewPayloadFields(payload?: Record<string, unknown> | null, limit?: number) {
  const normalizedPayload = payload
    ? normalizeDashboardPayload(payload) as Record<string, unknown>
    : null
  const fields = formatMemoryPayloadFields(normalizedPayload)
  return typeof limit === 'number' ? fields.slice(0, limit) : fields
}

/** 将 patch 的 before / after 值展开成逐字段展示行。*/
function previewPatchValueFields(fieldName: string, value: unknown): MemoryPayloadField[] {
  const normalizedFieldName = fieldName.trim()
  const normalizedValue = normalizeDashboardPayload(value, normalizedFieldName || null)

  if (!normalizedFieldName) {
    if (normalizedValue && typeof normalizedValue === 'object' && !Array.isArray(normalizedValue)) {
      return formatMemoryPayloadFields(normalizedValue as Record<string, unknown>)
    }
    return formatMemoryPayloadFields({ value: normalizedValue })
  }

  return formatMemoryPayloadFields({ [normalizedFieldName]: normalizedValue })
}

function normalizeDashboardPayload(value: unknown, fieldName?: string | null): Record<string, unknown> | unknown {
  if (Array.isArray(value)) {
    if (fieldName === 'companions') {
      return value.map((item) => resolveEntityCompanionLabel(item))
    }
    return value.map((item) => normalizeDashboardPayload(item, fieldName))
  }

  if (value && typeof value === 'object') {
    return Object.fromEntries(
      Object.entries(value as Record<string, unknown>).map(([key, nestedValue]) => [
        key,
        normalizeDashboardPayload(nestedValue, key),
      ]),
    )
  }

  if (fieldName === 'companions' && (typeof value === 'string' || (value && typeof value === 'object'))) {
    return resolveEntityCompanionLabel(value)
  }

  return value ?? null
}

function getPatchBeforeFields(patch: (typeof selectedEntityPatchUpdates.value)[number]) {
  return previewPatchValueFields(
    getEntityPatchFieldName(patch),
    patch.before ?? (patch.op === 'remove' ? patch.value : null),
  )
}

function getPatchAfterFields(patch: (typeof selectedEntityPatchUpdates.value)[number]) {
  return previewPatchValueFields(
    getEntityPatchFieldName(patch),
    patch.after ?? (patch.op !== 'remove' ? patch.value : null),
  )
}

/** 汇总一次操作中各层级变更数量。*/
function summarizeOperation(events: MemoryUpdateTimelineItem[]) {
  const segments = [
    { layer: 'semantic', count: events.filter((event) => event.memory_layer === 'semantic').length },
    { layer: 'entity_state', count: events.filter((event) => event.memory_layer === 'entity_state').length },
    { layer: 'episodic', count: events.filter((event) => event.memory_layer === 'episodic').length },
  ].filter((item) => item.count > 0)

  if (!segments.length) return '本批次没有可识别的结构化变动。'
  return segments.map((item) => `${getMemoryLayerLabel(item.layer)} ${item.count} 条`).join('，')
}

function getRoundStandaloneDesignLabels(round: StoryMemoryRoundView) {
  return round.designLabels.filter((item) => !round.contextLabels.includes(item))
}

// 会话总览卡片列表。
const allSessionCards = computed(() => {
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

const sessionCards = computed(() => {
  const keyword = sessionSearchTerm.value.trim().toLowerCase()
  return allSessionCards.value.filter((item) => {
    return !keyword || [
      item.storyTitle,
      item.sessionId,
      item.worldId,
      resolveWorldDisplay(item.worldId),
      item.latestReason,
      item.latestEventHeadline,
    ]
      .some((value) => String(value ?? '').toLowerCase().includes(keyword))
  })
})

// 包含失败事件的会话数量。
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

const {
  data: timelineResponse,
  isLoading: timelineLoading,
  isFetching: timelineFetching,
  error: timelineError,
  refetch: refetchTimeline,
} = useSessionMemoryTimelineQuery(selectedSessionId, 1, TIMELINE_FETCH_PAGE_SIZE)

// 时间线加载失败提示文案。
const timelineErrorMessage = computed(() => (
  timelineError.value instanceof Error ? timelineError.value.message : '无法获取当前 session 的时间线。'
))
// 当前会话时间线的有效数据源。
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
} = useSessionStoryMemoryQuery(selectedSessionId, 1, TIMELINE_FETCH_PAGE_SIZE)

// 当前会话 story memory 的有效数据源。
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

// 当前选中的会话卡片。
const selectedSessionCard = computed(() => (
  sessionCards.value.find((item) => item.sessionId === selectedSessionId.value) ?? null
))

// 当前会话 story memory 数据。
const selectedStoryMemory = computed(() => {
  if (effectiveStoryMemoryResponse.value?.story_memory) {
    return effectiveStoryMemoryResponse.value.story_memory
  }
  if (!selectedSessionId.value) return null
  return storySessionStore.getStoryMemorySession(selectedSessionId.value)?.storyMemory ?? null
})

const selectedStoryId = computed(() => {
  const storyId = effectiveStoryMemoryResponse.value?.story_id ?? selectedStoryMemory.value?.story_id ?? null
  return typeof storyId === 'string' && storyId.trim() ? storyId.trim() : undefined
})

const {
  data: selectedStoryResponse,
  isLoading: selectedStoryLoading,
  isFetching: selectedStoryFetching,
  error: selectedStoryError,
  refetch: refetchSelectedStory,
} = useStoryQuery(selectedStoryId)

const selectedStory = computed(() => selectedStoryResponse.value ?? null)

// 当前会话摘要快照。
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

// 当前会话时间线事件列表。
const selectedTimelineEvents = computed(() => {
  const timelineFromMemory = getStoryMemoryTimelineEvents(selectedStoryMemory.value, TIMELINE_FETCH_PAGE_SIZE)
  if (timelineFromMemory.length) return timelineFromMemory
  return effectiveTimelineResponse.value?.items ?? []
})

const selectedRoundCollection = computed(() => buildStoryMemoryRounds({
  story: selectedStory.value,
  events: selectedTimelineEvents.value,
}))

const selectedRoundViews = computed(() => selectedRoundCollection.value?.rounds ?? [])
const unassignedRoundEvents = computed(() => selectedRoundCollection.value?.unassignedEvents ?? [])

type StoryMemoryRoundPage = {
  id: string
  kind: 'round'
  label: string
  round: StoryMemoryRoundView
}

type StoryMemoryUnassignedPage = {
  id: string
  kind: 'unassigned'
  label: string
  events: MemoryUpdateTimelineItem[]
}

type StoryMemoryDetailPage = StoryMemoryRoundPage | StoryMemoryUnassignedPage

// 摘要生命周期说明文案。
const detailSummaryDescriptor = computed(() => {
  const state = effectiveTimelineResponse.value?.summary_state.state
    ?? deriveSummaryLifecycleState(selectedTimelineEvents.value, selectedSummarySnapshot.value)
  const reason = effectiveTimelineResponse.value?.summary_state.last_semantic_event?.reason
    ?? semanticEvents.value[0]?.reason
    ?? null
  return getSummaryLifecycleDescriptor(state, { reason })
})

// 语义层事件列表。
const semanticEvents = computed(() => selectedTimelineEvents.value.filter((event) => event.memory_layer === 'semantic'))
// 失败事件列表。
const failedEvents = computed(() => selectedTimelineEvents.value.filter((event) => event.status === 'failed'))
// 当前会话最近一条时间线事件。
const latestTimelineEvent = computed(() => {
  const items = selectedTimelineEvents.value
  return [...items].sort((a, b) => b.committed_at.localeCompare(a.committed_at))[0] ?? null
})

// 当前会话实体状态快照。
const selectedEntitySnapshot = computed(() => {
  const storyMemorySnapshot = getStoryMemoryEntitySnapshot(selectedStoryMemory.value)
  if (storyMemorySnapshot) return storyMemorySnapshot
  return selectedSessionId.value ? storySessionStore.getEntityStateSnapshot(selectedSessionId.value) : null
})

// 当前会话实体 patch 更新列表。
const selectedEntityPatchUpdates = computed(() => {
  const storyMemoryUpdates = getStoryMemoryEntityUpdates(selectedStoryMemory.value, 50)
  if (storyMemoryUpdates.length) return storyMemoryUpdates
  return selectedSessionId.value ? storySessionStore.getSessionEntityStateUpdates(selectedSessionId.value, 50) : []
})

// 当前会话世界更新快照。
const selectedWorldUpdate = computed(() => {
  const storyMemoryWorldUpdate = getStoryMemoryWorldUpdate(selectedStoryMemory.value)
  if (storyMemoryWorldUpdate) return storyMemoryWorldUpdate
  return selectedSessionId.value ? storySessionStore.getSessionWorldUpdate(selectedSessionId.value)?.payload ?? null : null
})

const selectedWorldId = computed(() => {
  const worldId = selectedStoryMemory.value?.world_id ?? selectedSessionCard.value?.worldId ?? null
  const normalizedWorldId = typeof worldId === 'string' ? worldId.trim() : ''
  return normalizedWorldId || undefined
})

const { data: selectedLorebookEntriesData } = useLorebookEntriesQuery(selectedWorldId)
const selectedLorebookCharacterEntries = computed(() => (
  (selectedLorebookEntriesData.value?.entries ?? []).filter((entry) => entry.type === 'character')
))

// 实体 ID 到展示名映射。
const selectedEntityNameMap = computed(() => buildEntityNameMap({
  snapshot: selectedEntitySnapshot.value,
  updates: selectedEntityPatchUpdates.value,
  events: selectedTimelineEvents.value,
  lorebookEntries: selectedLorebookCharacterEntries.value,
}))

// 实体状态风险提示列表。
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
    .flatMap((item) => item.companions.map((companion) => ({ owner: item.display_name, companion })))
    .filter(({ companion }) => {
      if (getEntityCompanionDisplayName(companion)) return false
      const companionId = getEntityCompanionId(companion)
      return !companionId || !selectedEntityNameMap.value.has(companionId)
    })
  if (unresolvedCompanions.length) {
    warnings.push(`存在未解析同行引用，最近来自：${unresolvedCompanions[0]?.owner ?? '未知角色'}`)
  }
  return warnings.slice(0, 3)
})

// 实体分布位置数量统计。
const selectedEntityLocationCount = computed(() => new Set(
  (selectedEntitySnapshot.value?.items ?? []).map((item) => item.current_location).filter(Boolean),
).size)
// 世界更新高亮摘要列表。
const selectedWorldUpdateHighlights = computed(() => extractWorldUpdateHighlights(selectedWorldUpdate.value).slice(0, 4))

// 最近一次语义层事件。
const latestSemanticEvent = computed(() => (
  effectiveTimelineResponse.value?.summary_state.last_semantic_event
  ?? semanticEvents.value[0]
  ?? null
))

const roundPages = computed<StoryMemoryDetailPage[]>(() => {
  const pages: StoryMemoryDetailPage[] = selectedRoundViews.value.map((round) => ({
    id: round.id,
    kind: 'round',
    label: `第 ${round.turn} 轮`,
    round,
  }))
  if (unassignedRoundEvents.value.length) {
    pages.push({
      id: 'unassigned-events',
      kind: 'unassigned',
      label: '未定位轮次',
      events: unassignedRoundEvents.value,
    })
  }
  return pages
})

const currentRoundPage = computed<StoryMemoryDetailPage | null>(() => (
  roundPages.value[detailPage.value - 1] ?? null
))
const currentRoundView = computed<StoryMemoryRoundPage | null>(() => (
  currentRoundPage.value?.kind === 'round' ? currentRoundPage.value : null
))
const currentUnassignedPage = computed<StoryMemoryUnassignedPage | null>(() => (
  currentRoundPage.value?.kind === 'unassigned' ? currentRoundPage.value : null
))
// 当前轮次总页数。
const detailPageCount = computed(() => Math.max(1, roundPages.value.length))
// 当前分页范围文案。
const historyRangeLabel = computed(() => {
  if (!roundPages.value.length) return '暂无轮次记忆'
  const current = currentRoundPage.value
  if (!current) return '暂无轮次记忆'
  if (current.kind === 'unassigned') return `未定位事件页 · 共 ${roundPages.value.length} 页`
  return `${current.label} · 共 ${roundPages.value.length} 页`
})

watch(detailPageCount, (count) => {
  if (detailPage.value > count) {
    dashboardStore.setDetailPage(count)
  }
}, { immediate: true })

/** 切换到上一页。*/
function goToPreviousPage() {
  if (detailPage.value > 1) {
    dashboardStore.setDetailPage(detailPage.value - 1)
  }
}

/** 切换到下一页。*/
function goToNextPage() {
  if (detailPage.value < detailPageCount.value) {
    dashboardStore.setDetailPage(detailPage.value + 1)
  }
}

/** 解析同行实体展示名。*/
function resolveEntityCompanionLabel(companion: unknown) {
  if (typeof companion !== 'string' && (!companion || typeof companion !== 'object')) {
    return '未知同行者'
  }
  return getEntityCompanionLabel(companion, selectedEntityNameMap.value)
}
</script>

<template>
  <div class="flex-1 overflow-auto bg-background">
    <div class="mx-auto w-full max-w-[1500px] px-4 py-4 sm:px-6 sm:py-6">
      <section class="rounded-[32px] border border-border bg-background p-4 shadow-sm sm:p-6">
        <div class="grid gap-6 xl:grid-cols-[360px_minmax(0,1fr)]">
          <aside>
            <Card class="rounded-[28px] border-stone-200/80 bg-white/90 shadow-none">
              <CardHeader class="gap-4">
                <div class="flex items-start justify-between gap-3">
                  <div>
                    <CardTitle class="text-stone-950">选择故事</CardTitle>
                    <CardDescription>左侧尽量只做一件事：选中要看的故事。</CardDescription>
                  </div>
                  <Button
                    variant="outline"
                    size="sm"
                    class="rounded-full border-stone-300 bg-white/90 text-stone-700"
                    @click="() => { refetchList(); refetchTimeline(); refetchStoryMemory(); refetchSelectedStory() }"
                  >
                    <RefreshCw class="h-3.5 w-3.5" :class="{ 'animate-spin': listFetching || timelineFetching || storyMemoryFetching || selectedStoryFetching }" />
                    刷新
                  </Button>
                </div>
              </CardHeader>

              <CardContent class="space-y-4">
                <div class="relative">
                  <Search class="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-stone-400" />
                  <Input
                    v-model="sessionSearchTerm"
                    class="h-11 rounded-2xl border-stone-200 bg-white pl-9"
                    placeholder="搜索故事名、世界名或 prompt"
                  />
                </div>

                <div class="rounded-[22px] border border-stone-200 bg-stone-50/75 px-4 py-3 text-xs text-stone-600">
                  <span>已命中 {{ sessionCards.length }} 个故事</span>
                  <span class="mx-2">·</span>
                  <span>需处理 {{ failedSessionCount }} 个</span>
                  <span class="mx-2">·</span>
                  <span>右侧单页只看一轮</span>
                </div>

                <div v-if="listLoading && !effectiveListResponse" class="rounded-[22px] border border-dashed border-stone-300 bg-stone-50/70 px-4 py-10 text-center text-sm text-stone-500">
                  正在加载故事列表…
                </div>

                <div v-else-if="listError" class="rounded-[22px] border border-rose-200 bg-rose-50 px-4 py-5 text-sm text-rose-900">
                  <p class="font-medium">故事列表加载失败</p>
                  <p class="mt-1 text-rose-800/80">{{ listErrorMessage }}</p>
                  <Button variant="outline" size="sm" class="mt-3 rounded-full border-rose-200 bg-white text-rose-700" @click="refetchList()">
                    重试
                  </Button>
                </div>

                <div v-else-if="!sessionCards.length" class="rounded-[22px] border border-dashed border-stone-300 bg-stone-50/70 px-4 py-10 text-center text-sm text-stone-500">
                  当前没有可选故事。
                </div>

                <div v-else class="space-y-3">
                  <div
                    v-for="item in sessionCards"
                    :key="item.sessionId"
                    role="button"
                    tabindex="0"
                    class="w-full rounded-[22px] border px-4 py-4 text-left transition-all"
                    :class="selectedSessionId === item.sessionId
                      ? 'border-stone-900 bg-stone-950 text-stone-50 shadow-[0_20px_40px_rgba(41,37,36,0.16)]'
                      : 'border-stone-200 bg-stone-50/80 text-stone-900 hover:border-stone-300 hover:bg-white'"
                    @click="dashboardStore.setSelectedSessionId(item.sessionId)"
                    @keydown.enter.prevent="dashboardStore.setSelectedSessionId(item.sessionId)"
                    @keydown.space.prevent="dashboardStore.setSelectedSessionId(item.sessionId)"
                  >
                    <div class="flex items-start justify-between gap-3">
                      <div class="min-w-0">
                        <p class="truncate text-base font-semibold">{{ item.storyTitle }}</p>
                        <p v-if="item.worldId" class="mt-1 text-xs opacity-70">{{ resolveWorldDisplay(item.worldId) }}</p>
                        <p class="mt-3 text-xs opacity-80">{{ item.latestEventHeadline }}</p>
                      </div>
                      <Badge
                        v-if="item.hasFailed"
                        class="border text-[10px]"
                        :class="statusBadgeClass('failed')"
                      >
                        需处理
                      </Badge>
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

                  <h2 class="hero-title mt-4 text-3xl text-stone-950">{{ selectedStory?.title || selectedSessionCard.storyTitle }}</h2>
                  <p class="mt-2 text-sm leading-6 text-stone-700">
                    {{ detailSummaryDescriptor.description }}
                  </p>

                  <div class="mt-4 flex flex-wrap gap-x-4 gap-y-2 text-xs text-stone-500">
                    <span>会话：{{ selectedSessionCard.sessionId }}</span>
                    <span v-if="selectedSessionCard.worldId">世界：{{ resolveWorldDisplay(selectedSessionCard.worldId) }}</span>
                    <span v-if="selectedStoryId">故事：{{ selectedStoryId }}</span>
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
                    <p class="text-[11px] uppercase tracking-[0.22em] text-stone-500">当前轮次页</p>
                    <p class="mt-2 text-sm font-semibold text-stone-950">{{ detailPage }} / {{ detailPageCount }}</p>
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
                  <CardHeader class="gap-4">
                    <div class="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
                      <div>
                        <CardTitle class="flex items-center gap-2 text-stone-950">
                          <CalendarRange class="h-4 w-4 text-stone-600" />
                          故事轮次记忆
                        </CardTitle>
                        <CardDescription>把当前页事件归到对应 prompt，只展示该轮使用的设定和关键记忆变动。</CardDescription>
                      </div>

                      <div class="flex flex-wrap items-center gap-2">
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
                      <span v-if="timelineFetching || storyMemoryFetching || selectedStoryFetching">正在刷新当前页…</span>
                    </div>
                  </CardHeader>
                  <CardContent class="space-y-4">
                    <div v-if="timelineLoading && !effectiveTimelineResponse" class="rounded-[22px] border border-dashed border-stone-300 bg-stone-50/70 px-4 py-10 text-center text-sm text-stone-500">
                      正在加载轮次记忆…
                    </div>

                    <div v-else-if="timelineError" class="rounded-[22px] border border-rose-200 bg-rose-50 px-4 py-5 text-sm text-rose-900">
                      <p class="font-medium">轮次记忆加载失败</p>
                      <p class="mt-1 text-rose-800/80">{{ timelineErrorMessage }}</p>
                      <Button variant="outline" size="sm" class="mt-3 rounded-full border-rose-200 bg-white text-rose-700" @click="refetchTimeline()">
                        重试
                      </Button>
                    </div>

                    <div v-else-if="selectedStoryId && selectedStoryError" class="rounded-[22px] border border-rose-200 bg-rose-50 px-4 py-5 text-sm text-rose-900">
                      <p class="font-medium">故事详情加载失败</p>
                      <p class="mt-1 text-rose-800/80">
                        {{ selectedStoryError instanceof Error ? selectedStoryError.message : '无法读取该会话对应的故事详情。' }}
                      </p>
                      <Button variant="outline" size="sm" class="mt-3 rounded-full border-rose-200 bg-white text-rose-700" @click="refetchSelectedStory()">
                        重试
                      </Button>
                    </div>

                    <div v-else-if="!selectedStoryId" class="rounded-[22px] border border-dashed border-stone-300 bg-stone-50/70 px-4 py-10 text-center text-sm text-stone-500">
                      当前会话没有可追溯的故事 ID，暂时无法按轮次还原 prompt。
                    </div>

                    <div v-else-if="selectedStoryLoading && !selectedStory" class="rounded-[22px] border border-dashed border-stone-300 bg-stone-50/70 px-4 py-10 text-center text-sm text-stone-500">
                      正在补全故事轮次信息…
                    </div>

                    <div v-else-if="!currentRoundPage" class="rounded-[22px] border border-dashed border-stone-300 bg-stone-50/70 px-4 py-10 text-center text-sm text-stone-500">
                      当前页没有可展示的轮次记忆。
                    </div>

                    <article
                      v-else-if="currentRoundView"
                      :key="currentRoundView.id"
                      class="rounded-[24px] border border-stone-200 bg-stone-50/80 p-4"
                    >
                      <div class="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
                        <div class="min-w-0 flex-1">
                          <div class="flex flex-wrap items-center gap-2">
                            <Badge variant="secondary" class="px-3 py-1 text-sm font-semibold">第 {{ currentRoundView.round.turn }} 轮</Badge>
                            <Badge class="border text-[10px]" :class="statusBadgeClass(currentRoundView.round.status)">
                              {{ getMemoryStatusLabel(currentRoundView.round.status) }}
                            </Badge>
                            <Badge variant="outline" class="text-[10px]">{{ currentRoundView.round.creationModeLabel }}</Badge>
                            <Badge v-if="currentRoundView.round.missingSegment" class="border border-amber-200 bg-amber-50 text-[10px] text-amber-700">
                              该轮故事段已缺失
                            </Badge>
                          </div>

                          <div class="mt-4 rounded-[24px] border border-stone-200 bg-white px-5 py-5 shadow-sm">
                            <p class="text-[11px] uppercase tracking-[0.22em] text-stone-500">用户 Prompt</p>
                            <p class="mt-3 text-lg font-semibold leading-8 text-stone-950">
                              {{ getExpandableText(`round-prompt-${currentRoundView.id}`, currentRoundView.round.prompt, 220) }}
                            </p>
                            <button
                              v-if="isTextTruncated(currentRoundView.round.prompt, 220)"
                              type="button"
                              class="mt-1 text-[11px] font-medium text-stone-500 underline-offset-4 hover:underline"
                              @click="toggleTextExpansion(`round-prompt-${currentRoundView.id}`)"
                            >
                              {{ isTextExpanded(`round-prompt-${currentRoundView.id}`) ? '收起 Prompt' : '展开 Prompt' }}
                            </button>
                          </div>

                          <div class="mt-4 flex flex-wrap gap-2">
                            <Badge
                              v-for="label in currentRoundView.round.contextLabels"
                              :key="`${currentRoundView.id}-context-${label}`"
                              class="border border-sky-200 bg-sky-50 text-[11px] font-normal text-sky-800"
                            >
                              设定 · {{ label }}
                            </Badge>
                            <Badge
                              v-for="label in getRoundStandaloneDesignLabels(currentRoundView.round)"
                              :key="`${currentRoundView.id}-design-${label}`"
                              class="border border-stone-200 bg-white text-[11px] font-normal text-stone-700"
                            >
                              {{ label }}
                            </Badge>
                          </div>

                          <p v-if="!currentRoundView.round.contextLabels.length && !currentRoundView.round.designLabels.length" class="mt-3 text-xs text-stone-500">
                            该轮没有保存可读的设定摘要。
                          </p>
                        </div>

                        <div class="rounded-[22px] border border-white/90 bg-white/85 px-4 py-3 text-sm text-stone-700 lg:w-[220px]">
                          <p class="text-[11px] uppercase tracking-[0.22em] text-stone-500">该轮记忆变动</p>
                          <p class="mt-2 font-semibold text-stone-950">{{ summarizeOperation(currentRoundView.round.events) }}</p>
                          <p class="mt-2 text-xs text-stone-500">{{ formatTimestamp(currentRoundView.round.timestamp ?? currentRoundView.round.events[0]?.committed_at) }}</p>
                        </div>
                      </div>

                      <div class="mt-4 space-y-3">
                        <article
                          v-for="event in currentRoundView.round.events.slice(0, 6)"
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
                            <span>{{ formatTimestamp(event.committed_at) }}</span>
                          </div>

                          <div v-if="previewPayloadFields(event.after, 3).length || previewPayloadFields(event.before, 3).length" class="mt-4 grid gap-3 lg:grid-cols-2">
                            <div v-if="previewPayloadFields(event.before, 3).length" class="rounded-2xl border border-stone-200 bg-stone-50/80 px-3 py-3">
                              <p class="text-[11px] uppercase tracking-[0.22em] text-stone-500">变更前</p>
                              <p
                                v-for="field in previewPayloadFields(event.before, 3)"
                                :key="`round-before-${event.event_id}-${field.label}`"
                                class="mt-2 text-sm leading-6 text-stone-700"
                              >
                                <span class="font-medium text-stone-500">{{ field.label }}：</span>{{ getExpandableText(`round-before-${event.event_id}-${field.label}`, field.value, 84) }}
                              </p>
                            </div>
                            <div v-if="previewPayloadFields(event.after, 3).length" class="rounded-2xl border border-stone-200 bg-stone-50/80 px-3 py-3">
                              <p class="text-[11px] uppercase tracking-[0.22em] text-stone-500">变更后</p>
                              <p
                                v-for="field in previewPayloadFields(event.after, 3)"
                                :key="`round-after-${event.event_id}-${field.label}`"
                                class="mt-2 text-sm leading-6 text-stone-700"
                              >
                                <span class="font-medium text-stone-500">{{ field.label }}：</span>{{ getExpandableText(`round-after-${event.event_id}-${field.label}`, field.value, 84) }}
                              </p>
                            </div>
                          </div>
                        </article>

                        <p v-if="currentRoundView.round.events.length > 6" class="text-xs text-stone-500">
                          还有 {{ currentRoundView.round.events.length - 6 }} 条事件未展开。
                        </p>
                      </div>
                    </article>

                    <article v-else-if="currentUnassignedPage" class="rounded-[24px] border border-amber-200 bg-amber-50/80 p-4">
                      <div class="flex flex-wrap items-center gap-2">
                        <Badge class="border border-amber-200 bg-amber-100 text-[10px] text-amber-700">未定位轮次</Badge>
                        <Badge class="border text-[10px]" :class="statusBadgeClass(currentUnassignedPage.events.some((event) => event.status === 'failed') ? 'failed' : 'committed')">
                          {{ currentUnassignedPage.events.length }} 条事件
                        </Badge>
                      </div>
                      <p class="mt-3 text-sm leading-6 text-amber-900">
                        这些事件缺少 `source_turn`，当前只能保留在会话级，无法可靠归到具体 prompt。
                      </p>

                      <div class="mt-4 space-y-3">
                        <article
                          v-for="event in currentUnassignedPage.events.slice(0, 6)"
                          :key="`unassigned-${event.event_id}`"
                          class="rounded-[22px] border border-white/90 bg-white/92 p-4"
                        >
                          <div class="flex flex-wrap items-center gap-2">
                            <Badge class="border text-[10px]" :class="layerBadgeClass(event.memory_layer)">
                              {{ getMemoryLayerLabel(event.memory_layer) }}
                            </Badge>
                            <Badge class="border text-[10px]" :class="statusBadgeClass(event.status)">
                              {{ getMemoryStatusLabel(event.status) }}
                            </Badge>
                          </div>

                          <p class="mt-3 text-sm font-semibold text-stone-950">{{ buildEventHeadline(event) }}</p>
                          <p class="mt-1 text-sm leading-6 text-stone-700">{{ event.reason || event.title }}</p>
                          <div class="mt-3 flex flex-wrap gap-x-4 gap-y-2 text-[11px] text-stone-500">
                            <span>{{ getMemorySourceLabel(event.source) }}</span>
                            <span>{{ formatTimestamp(event.committed_at) }}</span>
                          </div>
                        </article>
                      </div>
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
                          <span
                            v-for="field in getPatchBeforeFields(patch)"
                            :key="`patch-before-${getEntityPatchEventId(patch)}-${field.label}`"
                            class="block"
                          >
                            <span class="font-medium text-stone-500">{{ field.label }}：</span>{{ getExpandableText(`patch-before-${getEntityPatchEventId(patch)}-${field.label}`, field.value, 72) }}
                          </span>
                        </p>
                        <button
                          v-for="field in getPatchBeforeFields(patch).filter((item) => isTextTruncated(item.value, 72))"
                          :key="`patch-before-toggle-${getEntityPatchEventId(patch)}-${field.label}`"
                          type="button"
                          class="mt-1 text-[11px] font-medium text-stone-500 underline-offset-4 hover:underline"
                          @click="toggleTextExpansion(`patch-before-${getEntityPatchEventId(patch)}-${field.label}`)"
                        >
                          {{ isTextExpanded(`patch-before-${getEntityPatchEventId(patch)}-${field.label}`) ? `收起${field.label}` : `展开${field.label}` }}
                        </button>
                      </div>
                      <div class="rounded-2xl border border-emerald-200 bg-emerald-50/70 px-3 py-3">
                        <p class="text-[11px] uppercase tracking-[0.22em] text-emerald-700">变更后</p>
                        <p class="mt-2 text-sm leading-6 text-stone-800">
                          <span
                            v-for="field in getPatchAfterFields(patch)"
                            :key="`patch-after-${getEntityPatchEventId(patch)}-${field.label}`"
                            class="block"
                          >
                            <span class="font-medium text-emerald-700">{{ field.label }}：</span>{{ getExpandableText(`patch-after-${getEntityPatchEventId(patch)}-${field.label}`, field.value, 72) }}
                          </span>
                        </p>
                        <button
                          v-for="field in getPatchAfterFields(patch).filter((item) => isTextTruncated(item.value, 72))"
                          :key="`patch-after-toggle-${getEntityPatchEventId(patch)}-${field.label}`"
                          type="button"
                          class="mt-1 text-[11px] font-medium text-emerald-700 underline-offset-4 hover:underline"
                          @click="toggleTextExpansion(`patch-after-${getEntityPatchEventId(patch)}-${field.label}`)"
                        >
                          {{ isTextExpanded(`patch-after-${getEntityPatchEventId(patch)}-${field.label}`) ? `收起${field.label}` : `展开${field.label}` }}
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
.hero-title {
  font-family: "Noto Serif SC", "Source Han Serif SC", "Songti SC", "STSong", serif;
  letter-spacing: -0.02em;
}
</style>
