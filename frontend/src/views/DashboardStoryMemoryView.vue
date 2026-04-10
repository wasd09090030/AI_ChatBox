<script setup lang="ts">
import { storeToRefs } from 'pinia'
import { computed, watch } from 'vue'
import {
  AlertTriangle,
  Brain,
  CalendarRange,
  History,
  Layers3,
  MapPinned,
  Package,
  RefreshCw,
  Search,
  Sparkles,
  TimerReset,
  Users,
} from 'lucide-vue-next'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import {
  useMemoryUpdatesQuery,
  useSessionMemoryTimelineQuery,
  useSessionStoryMemoryQuery,
} from '@/domains/memory/queries/useMemoryUpdateQueries'
import type { MemoryUpdateTimelineItem } from '@/domains/memory/api/memoryUpdatesApi'
import {
  deriveSummaryLifecycleState,
  formatMemoryPayloadFields,
  getMemorySourceLabel,
  getSummaryLifecycleDescriptor,
  groupMemoryEventsByOperation,
  type SummaryLifecycleState,
} from '@/domains/memory/memoryUpdatePresentation'
import {
  extractWorldUpdateHighlights,
  getEntityPatchCommittedAt,
  getEntityPatchDetail,
  getEntityPatchEvidenceText,
  getEntityPatchEventId,
  getEntityPatchHeadline,
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

const storySessionStore = useStorySessionStore()
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
  detailTab,
  listSnapshot,
  queryFilters,
} = storeToRefs(dashboardStore)

const sourceOptions = [
  { value: 'all', label: '全部来源' },
  { value: 'generate', label: 'generate' },
  { value: 'rollback', label: 'rollback' },
  { value: 'regenerate', label: 'regenerate' },
  { value: 'story_adjustment_commit', label: 'story_adjustment_commit' },
] as const

const layerOptions = [
  { value: 'all', label: '全部层级' },
  { value: 'episodic', label: 'episodic' },
  { value: 'semantic', label: 'semantic' },
  { value: 'entity_state', label: 'entity_state' },
] as const

const statusOptions = [
  { value: 'all', label: '全部状态' },
  { value: 'committed', label: 'committed' },
  { value: 'failed', label: 'failed' },
  { value: 'stale', label: 'stale' },
] as const

const timeRangeOptions = [
  { value: 'all', label: '全部时间' },
  { value: '1h', label: '最近 1 小时' },
  { value: '24h', label: '最近 24 小时' },
  { value: '7d', label: '最近 7 天' },
] as const

const summaries = computed(() => storySessionStore.getAllSummaries())
const summaryMap = computed(() => new Map(summaries.value.map((record) => [record.sessionId, record])))
const storyMemorySessionMap = computed(() => new Map(
  storySessionStore.getAllStoryMemorySessions().map((record) => [record.sessionId, record]),
))

const {
  data: listResponse,
  isLoading: listLoading,
  isFetching: listFetching,
  error: listError,
  refetch: refetchList,
} = useMemoryUpdatesQuery(queryFilters)

const listErrorMessage = computed(() => (
  listError.value instanceof Error ? listError.value.message : '无法获取服务端记忆事件列表。'
))
const effectiveListResponse = computed(() => listResponse.value ?? listSnapshot.value ?? null)

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
      return {
        sessionId,
        summary,
        storyMemorySession,
        entitySnapshot,
        summaryState,
        summaryDescriptor: getSummaryLifecycleDescriptor(summaryState),
        storyTitle: storyMemorySession?.storyTitle ?? summary?.storyTitle ?? sessionId,
        worldId: storyMemory?.world_id ?? latestWorldId ?? summary?.worldId ?? '',
        latestEvent,
        eventCount: effectiveEvents.length,
        semanticCount: effectiveEvents.filter((item) => item.memory_layer === 'semantic').length,
        episodicCount: effectiveEvents.filter((item) => item.memory_layer === 'episodic').length,
        entityCount: getStoryMemoryEntityUpdates(storyMemory, 500).length
          || effectiveEvents.filter((item) => item.memory_layer === 'entity_state').length,
        trackedEntities: entitySnapshot?.total ?? 0,
        hasFailed: storyMemory?.operation?.status === 'failed' || effectiveEvents.some((item) => item.status === 'failed'),
      }
    })
    .sort((a, b) => (b.latestEvent?.committed_at ?? '').localeCompare(a.latestEvent?.committed_at ?? ''))
})

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
} = useSessionMemoryTimelineQuery(selectedSessionId, detailPage, detailPageSize)

const timelineErrorMessage = computed(() => (
  timelineError.value instanceof Error ? timelineError.value.message : '无法获取当前 session 的时间线。'
))
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
} = useSessionStoryMemoryQuery(
  selectedSessionId,
  detailPage,
  detailPageSize,
)

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

const selectedSessionCard = computed(() => (
  sessionCards.value.find((item) => item.sessionId === selectedSessionId.value) ?? null
))

const selectedStoryMemory = computed(() => {
  if (effectiveStoryMemoryResponse.value?.story_memory) {
    return effectiveStoryMemoryResponse.value.story_memory
  }
  if (!selectedSessionId.value) return null
  return storySessionStore.getStoryMemorySession(selectedSessionId.value)?.storyMemory ?? null
})

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

const detailSummaryDescriptor = computed(() => {
  const state = effectiveTimelineResponse.value?.summary_state.state
    ?? deriveSummaryLifecycleState(selectedTimelineEvents.value, selectedSummarySnapshot.value)
  const reason = effectiveTimelineResponse.value?.summary_state.last_semantic_event?.reason
    ?? semanticEvents.value[0]?.reason
    ?? null
  return getSummaryLifecycleDescriptor(state, { reason })
})

const selectedTimelineEvents = computed(() => {
  const timelineFromMemory = getStoryMemoryTimelineEvents(selectedStoryMemory.value, detailPageSize.value)
  if (timelineFromMemory.length) return timelineFromMemory
  return effectiveTimelineResponse.value?.items ?? []
})

const operationGroups = computed(() => groupMemoryEventsByOperation(selectedTimelineEvents.value))
const semanticEvents = computed(() => selectedTimelineEvents.value.filter((event) => event.memory_layer === 'semantic'))
const entityEvents = computed(() => selectedTimelineEvents.value.filter((event) => event.memory_layer === 'entity_state'))
const failedEvents = computed(() => selectedTimelineEvents.value.filter((event) => event.status === 'failed'))
const latestTimelineEvent = computed(() => {
  const items = selectedTimelineEvents.value
  return [...items].sort((a, b) => b.committed_at.localeCompare(a.committed_at))[0] ?? null
})
const selectedEntitySnapshot = computed(() => {
  const storyMemorySnapshot = getStoryMemoryEntitySnapshot(selectedStoryMemory.value)
  if (storyMemorySnapshot) return storyMemorySnapshot
  return selectedSessionId.value ? storySessionStore.getEntityStateSnapshot(selectedSessionId.value) : null
})
const selectedEntityPatchUpdates = computed(() => {
  const storyMemoryUpdates = getStoryMemoryEntityUpdates(selectedStoryMemory.value, 50)
  if (storyMemoryUpdates.length) return storyMemoryUpdates
  return selectedSessionId.value ? storySessionStore.getSessionEntityStateUpdates(selectedSessionId.value, 50) : []
})
const selectedWorldUpdate = computed(() => {
  const storyMemoryWorldUpdate = getStoryMemoryWorldUpdate(selectedStoryMemory.value)
  if (storyMemoryWorldUpdate) return storyMemoryWorldUpdate
  return selectedSessionId.value ? storySessionStore.getSessionWorldUpdate(selectedSessionId.value)?.payload ?? null : null
})
const selectedEntityNameMap = computed(() => new Map(
  (selectedEntitySnapshot.value?.items ?? []).map((item) => [item.entity_id, item.display_name]),
))
const selectedEntityWarnings = computed(() => {
  const items = selectedEntitySnapshot.value?.items ?? []
  if (!items.length) return ['当前会话还没有缓存到实体状态快照。']

  const warnings: string[] = []
  const missingLocation = items.filter((item) => !item.current_location)
  if (missingLocation.length) {
    warnings.push(`缺少明确地点：${missingLocation.slice(0, 4).map((item) => item.display_name).join('、')}`)
  }
  const missingEvidence = items.filter((item) => !item.evidence.length)
  if (missingEvidence.length) {
    warnings.push(`缺少文本证据：${missingEvidence.slice(0, 4).map((item) => item.display_name).join('、')}`)
  }
  const unresolvedCompanions = items
    .flatMap((item) => item.companions.map((companionId) => ({ owner: item.display_name, companionId })))
    .filter((item) => !selectedEntityNameMap.value.has(item.companionId))
  if (unresolvedCompanions.length) {
    warnings.push(`存在未解析同行引用，最近来自：${unresolvedCompanions[0]?.owner ?? '未知角色'}`)
  }
  return warnings.slice(0, 3)
})
const selectedEntityLocationCount = computed(() => new Set(
  (selectedEntitySnapshot.value?.items ?? []).map((item) => item.current_location).filter(Boolean),
).size)
const selectedWorldUpdateHighlights = computed(() => extractWorldUpdateHighlights(selectedWorldUpdate.value))

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

function statusBadgeClass(status?: string | null) {
  if (status === 'failed') return 'bg-rose-50 text-rose-700 border-rose-200'
  if (status === 'stale') return 'bg-amber-50 text-amber-700 border-amber-200'
  return 'bg-emerald-50 text-emerald-700 border-emerald-200'
}

function layerBadgeClass(layer: string) {
  if (layer === 'semantic') return 'bg-violet-50 text-violet-700 border-violet-200'
  if (layer === 'episodic') return 'bg-sky-50 text-sky-700 border-sky-200'
  if (layer === 'entity_state') return 'bg-orange-50 text-orange-700 border-orange-200'
  return 'bg-stone-50 text-stone-700 border-stone-200'
}

function summaryStateLabel(state?: string | null) {
  return getSummaryLifecycleDescriptor((state as SummaryLifecycleState | null) ?? 'absent').label
}

function stringifyPayload(payload?: Record<string, unknown> | null) {
  if (!payload) return ''
  return JSON.stringify(payload, null, 2)
}

function resolveEntityCompanionLabel(companionId: string) {
  return selectedEntityNameMap.value.get(companionId) ?? companionId
}
</script>

<template>
  <div class="flex-1 overflow-auto bg-[radial-gradient(circle_at_top_left,_rgba(14,165,233,0.09),_transparent_28%),radial-gradient(circle_at_top_right,_rgba(249,115,22,0.08),_transparent_24%),linear-gradient(180deg,_rgba(248,250,252,0.98),_rgba(255,255,255,1))]">
    <div class="mx-auto flex w-full max-w-7xl flex-col gap-6 px-6 py-6">
      <section class="overflow-hidden rounded-[28px] border border-border/70 bg-background/95 shadow-sm shadow-black/5">
        <div class="grid gap-6 px-6 py-6 lg:grid-cols-[minmax(0,1.15fr)_minmax(320px,0.85fr)]">
          <div class="space-y-4">
            <div class="inline-flex items-center gap-2 rounded-full border border-sky-200 bg-sky-50 px-3 py-1 text-xs font-medium text-sky-700">
              <Sparkles class="h-3.5 w-3.5" />
              管理区 · 故事记忆审计台
            </div>
            <div>
              <h1 class="text-2xl font-semibold tracking-tight text-foreground">故事记忆总览</h1>
              <p class="mt-2 max-w-3xl text-sm leading-6 text-muted-foreground">
                从服务端 journal 直接回看生成、回滚、重生成和正文调整后的摘要更新、历史修复与语义重建链路。
              </p>
            </div>
            <div class="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
              <div class="rounded-2xl border border-border/70 bg-muted/20 px-4 py-3">
                <p class="text-xs uppercase tracking-wide text-muted-foreground">本地摘要快照</p>
                <p class="mt-2 text-2xl font-semibold text-foreground">{{ summaries.length }}</p>
              </div>
              <div class="rounded-2xl border border-border/70 bg-muted/20 px-4 py-3">
                <p class="text-xs uppercase tracking-wide text-muted-foreground">命中事件数</p>
                <p class="mt-2 text-2xl font-semibold text-foreground">{{ effectiveListResponse?.total ?? 0 }}</p>
              </div>
              <div class="rounded-2xl border border-border/70 bg-muted/20 px-4 py-3">
                <p class="text-xs uppercase tracking-wide text-muted-foreground">会话数</p>
                <p class="mt-2 text-2xl font-semibold text-foreground">{{ sessionCards.length }}</p>
              </div>
              <div class="rounded-2xl border border-border/70 bg-muted/20 px-4 py-3">
                <p class="text-xs uppercase tracking-wide text-muted-foreground">失败事件</p>
                <p class="mt-2 text-2xl font-semibold text-foreground">{{ failedEvents.length }}</p>
              </div>
            </div>
          </div>

          <div class="rounded-[24px] border border-sky-200/70 bg-[linear-gradient(180deg,rgba(240,249,255,0.9),rgba(255,255,255,0.92))] p-5">
            <div class="flex items-start justify-between gap-3">
              <div>
                <p class="text-sm font-semibold text-sky-900">当前选中会话</p>
                <p class="mt-1 text-xs leading-5 text-sky-800/80">
                  这里聚合展示语义状态、最近一次事件和失败信号，方便快速判定当前链路是否健康。
                </p>
              </div>
              <Badge
                v-if="selectedSessionCard"
                class="border text-[10px]"
                :class="selectedSessionCard.summaryDescriptor.badgeTone"
              >
                {{ selectedSessionCard.summaryDescriptor.label }}
              </Badge>
            </div>

            <div v-if="selectedSessionCard" class="mt-4 space-y-3">
              <div class="rounded-2xl border border-white/70 bg-white/75 px-4 py-3">
                <p class="text-sm font-semibold text-foreground">{{ selectedSessionCard.storyTitle }}</p>
                <p class="mt-1 text-[11px] font-mono text-muted-foreground">{{ selectedSessionCard.sessionId }}</p>
                <p v-if="selectedSessionCard.worldId" class="mt-1 text-[11px] text-muted-foreground">世界：{{ selectedSessionCard.worldId }}</p>
              </div>
              <div class="grid gap-3 sm:grid-cols-3">
                <div class="rounded-2xl border border-white/70 bg-white/75 px-3 py-3">
                  <p class="text-[11px] uppercase tracking-wide text-muted-foreground">最近事件</p>
                  <p class="mt-2 text-sm font-medium text-foreground">{{ selectedSessionCard.latestEvent?.title ?? '暂无' }}</p>
                </div>
                <div class="rounded-2xl border border-white/70 bg-white/75 px-3 py-3">
                  <p class="text-[11px] uppercase tracking-wide text-muted-foreground">事件计数</p>
                  <p class="mt-2 text-sm font-medium text-foreground">{{ selectedSessionCard.eventCount }} 条</p>
                </div>
                <div class="rounded-2xl border border-white/70 bg-white/75 px-3 py-3">
                  <p class="text-[11px] uppercase tracking-wide text-muted-foreground">最近时间</p>
                  <p class="mt-2 text-sm font-medium text-foreground">{{ formatTimestamp(selectedSessionCard.latestEvent?.committed_at) }}</p>
                </div>
              </div>
              <div class="grid gap-3 sm:grid-cols-3">
                <div class="rounded-2xl border border-white/70 bg-white/75 px-3 py-3">
                  <p class="text-[11px] uppercase tracking-wide text-muted-foreground">实体快照</p>
                  <p class="mt-2 text-sm font-medium text-foreground">{{ selectedSessionCard.trackedEntities }} 人</p>
                </div>
                <div class="rounded-2xl border border-white/70 bg-white/75 px-3 py-3">
                  <p class="text-[11px] uppercase tracking-wide text-muted-foreground">实体事件</p>
                  <p class="mt-2 text-sm font-medium text-foreground">{{ selectedSessionCard.entityCount }} 条</p>
                </div>
                <div class="rounded-2xl border border-white/70 bg-white/75 px-3 py-3">
                  <p class="text-[11px] uppercase tracking-wide text-muted-foreground">地点数</p>
                  <p class="mt-2 text-sm font-medium text-foreground">{{ selectedEntityLocationCount }}</p>
                </div>
              </div>
            </div>

            <div v-else class="mt-4 rounded-2xl border border-dashed border-sky-200 bg-white/70 px-4 py-6 text-sm text-sky-900/80">
              当前筛选条件下没有可选会话。
            </div>
          </div>
        </div>
      </section>

      <section class="grid gap-6 xl:grid-cols-[minmax(340px,0.92fr)_minmax(0,1.5fr)]">
        <Card class="border-border/70 bg-background/90 shadow-sm shadow-black/5">
          <CardHeader class="gap-4">
            <div class="flex items-start justify-between gap-3">
              <div>
                <CardTitle class="flex items-center gap-2">
                  <Search class="h-4 w-4 text-sky-600" />
                  全局筛选
                </CardTitle>
                <CardDescription>按来源、层级、状态和时间范围定位会话，再进入右侧审计详情。</CardDescription>
              </div>
              <button
                class="inline-flex items-center gap-2 rounded-md border border-border px-3 py-1.5 text-xs text-muted-foreground transition-colors hover:bg-muted"
                @click="() => { refetchList(); refetchTimeline(); refetchStoryMemory() }"
              >
                <RefreshCw class="h-3.5 w-3.5" :class="{ 'animate-spin': listFetching || timelineFetching || storyMemoryFetching }" />
                刷新
              </button>
            </div>

            <div class="grid gap-3">
              <div class="relative">
                <Search class="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                <Input
                  v-model="searchTerm"
                  class="pl-9"
                  placeholder="按 session、世界 ID、标题或原因搜索"
                />
              </div>

              <div class="grid gap-3 sm:grid-cols-2">
                <Select v-model="selectedSource">
                  <SelectTrigger class="h-10">
                    <SelectValue placeholder="选择来源" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem v-for="option in sourceOptions" :key="option.value" :value="option.value">
                      {{ option.label }}
                    </SelectItem>
                  </SelectContent>
                </Select>

                <Select v-model="selectedLayer">
                  <SelectTrigger class="h-10">
                    <SelectValue placeholder="选择层级" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem v-for="option in layerOptions" :key="option.value" :value="option.value">
                      {{ option.label }}
                    </SelectItem>
                  </SelectContent>
                </Select>

                <Select v-model="selectedStatus">
                  <SelectTrigger class="h-10">
                    <SelectValue placeholder="选择状态" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem v-for="option in statusOptions" :key="option.value" :value="option.value">
                      {{ option.label }}
                    </SelectItem>
                  </SelectContent>
                </Select>

                <Select v-model="selectedTimeRange">
                  <SelectTrigger class="h-10">
                    <SelectValue placeholder="选择时间范围" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem v-for="option in timeRangeOptions" :key="option.value" :value="option.value">
                      {{ option.label }}
                    </SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>
          </CardHeader>

          <CardContent>
            <div v-if="listLoading && !effectiveListResponse" class="rounded-2xl border border-dashed border-border/70 bg-muted/10 px-4 py-10 text-center text-sm text-muted-foreground">
              正在加载服务端记忆事件…
            </div>

            <div v-else-if="listError" class="rounded-2xl border border-rose-200 bg-rose-50 px-4 py-5 text-sm text-rose-900">
              <p class="font-medium">全局事件查询失败</p>
              <p class="mt-1 text-rose-800/80">{{ listErrorMessage }}</p>
              <button class="mt-3 rounded-md border border-rose-200 bg-white px-3 py-1.5 text-xs text-rose-700" @click="refetchList()">
                重试
              </button>
            </div>

            <div v-else-if="!sessionCards.length" class="rounded-2xl border border-dashed border-border/70 bg-muted/10 px-4 py-10 text-center text-sm text-muted-foreground">
              尚未产生任何记忆变动事件，或当前筛选条件下没有命中结果。
            </div>

            <div v-else class="space-y-3">
              <button
                v-for="item in sessionCards"
                :key="item.sessionId"
                class="w-full rounded-[22px] border px-4 py-4 text-left transition-colors"
                :class="selectedSessionId === item.sessionId ? 'border-sky-300 bg-sky-50/70 shadow-sm' : 'border-border/70 bg-muted/10 hover:bg-muted/20'"
                @click="dashboardStore.setSelectedSessionId(item.sessionId)"
              >
                <div class="flex items-start justify-between gap-3">
                  <div class="min-w-0">
                    <p class="truncate text-sm font-semibold text-foreground">{{ item.storyTitle }}</p>
                    <p class="mt-1 truncate text-[11px] font-mono text-muted-foreground">{{ item.sessionId }}</p>
                    <p v-if="item.worldId" class="mt-1 text-[11px] text-muted-foreground">世界：{{ item.worldId }}</p>
                  </div>
                  <div class="flex shrink-0 flex-wrap justify-end gap-1.5">
                    <Badge class="border text-[10px]" :class="item.summaryDescriptor.badgeTone">
                      {{ item.summaryDescriptor.label }}
                    </Badge>
                    <Badge variant="secondary" class="text-[10px]">{{ item.eventCount }} 条</Badge>
                    <Badge class="border text-[10px]" :class="layerBadgeClass('semantic')">S {{ item.semanticCount }}</Badge>
                    <Badge class="border text-[10px]" :class="layerBadgeClass('episodic')">E {{ item.episodicCount }}</Badge>
                    <Badge class="border text-[10px]" :class="layerBadgeClass('entity_state')">T {{ item.entityCount }}</Badge>
                    <Badge v-if="item.hasFailed" class="border text-[10px]" :class="statusBadgeClass('failed')">failed</Badge>
                  </div>
                </div>
                <p class="mt-3 text-xs text-muted-foreground">{{ item.latestEvent?.title ?? '暂无事件' }}</p>
                <p class="mt-1 text-[11px] text-muted-foreground">{{ formatTimestamp(item.latestEvent?.committed_at) }}</p>
                <p class="mt-2 text-[11px] text-muted-foreground">当前实体快照：{{ item.trackedEntities }} 人</p>
              </button>
            </div>
          </CardContent>
        </Card>

        <Card class="border-border/70 bg-background/90 shadow-sm shadow-black/5">
          <CardHeader class="gap-4">
            <div class="flex items-start justify-between gap-3">
              <div>
                <CardTitle class="flex items-center gap-2">
                  <History class="h-4 w-4 text-sky-600" />
                  会话审计详情
                </CardTitle>
                <CardDescription>按操作批次查看事件链路，同时提供独立的语义摘要视图。</CardDescription>
              </div>
              <Badge v-if="selectedSessionId" variant="outline" class="text-[10px] font-mono">{{ selectedSessionId }}</Badge>
            </div>
          </CardHeader>

          <CardContent>
            <div v-if="!selectedSessionId" class="rounded-2xl border border-dashed border-border/70 bg-muted/10 px-4 py-12 text-center text-sm text-muted-foreground">
              请选择左侧会话查看详情。
            </div>

            <div v-else-if="timelineLoading && !effectiveTimelineResponse" class="rounded-2xl border border-dashed border-border/70 bg-muted/10 px-4 py-12 text-center text-sm text-muted-foreground">
              正在加载会话时间线…
            </div>

            <div v-else-if="timelineError" class="rounded-2xl border border-rose-200 bg-rose-50 px-4 py-5 text-sm text-rose-900">
              <p class="font-medium">会话时间线加载失败</p>
              <p class="mt-1 text-rose-800/80">{{ timelineErrorMessage }}</p>
              <button class="mt-3 rounded-md border border-rose-200 bg-white px-3 py-1.5 text-xs text-rose-700" @click="refetchTimeline()">
                重试
              </button>
            </div>

            <div v-else-if="effectiveTimelineResponse" class="space-y-4">
              <div class="grid gap-3 lg:grid-cols-3">
                <div class="rounded-[22px] border px-4 py-4" :class="detailSummaryDescriptor.tone">
                  <div class="flex items-start justify-between gap-3">
                    <div>
                      <p class="text-sm font-semibold">{{ detailSummaryDescriptor.label }}</p>
                      <p class="mt-2 text-xs leading-5">{{ detailSummaryDescriptor.description }}</p>
                    </div>
                    <Brain class="h-4 w-4 shrink-0" />
                  </div>
                </div>

                <div class="rounded-[22px] border border-border/70 bg-muted/10 px-4 py-4">
                  <div class="flex items-center gap-2">
                    <Layers3 class="h-4 w-4 text-sky-600" />
                    <p class="text-sm font-semibold text-foreground">事件密度</p>
                  </div>
                  <div class="mt-3 grid grid-cols-4 gap-2 text-xs">
                    <div class="rounded-xl border border-border/60 bg-background/80 px-3 py-2">
                      <p class="text-muted-foreground">总数</p>
                      <p class="mt-1 text-sm font-semibold text-foreground">{{ effectiveStoryMemoryResponse?.timeline_total ?? effectiveTimelineResponse.total }}</p>
                    </div>
                    <div class="rounded-xl border border-border/60 bg-background/80 px-3 py-2">
                      <p class="text-muted-foreground">Semantic</p>
                      <p class="mt-1 text-sm font-semibold text-foreground">{{ semanticEvents.length }}</p>
                    </div>
                    <div class="rounded-xl border border-border/60 bg-background/80 px-3 py-2">
                      <p class="text-muted-foreground">Entity</p>
                      <p class="mt-1 text-sm font-semibold text-foreground">{{ entityEvents.length }}</p>
                    </div>
                    <div class="rounded-xl border border-border/60 bg-background/80 px-3 py-2">
                      <p class="text-muted-foreground">Patch</p>
                      <p class="mt-1 text-sm font-semibold text-foreground">{{ selectedEntityPatchUpdates.length }}</p>
                    </div>
                    <div class="rounded-xl border border-border/60 bg-background/80 px-3 py-2">
                      <p class="text-muted-foreground">失败</p>
                      <p class="mt-1 text-sm font-semibold text-foreground">{{ failedEvents.length }}</p>
                    </div>
                  </div>
                </div>

                <div class="rounded-[22px] border border-border/70 bg-muted/10 px-4 py-4">
                  <div class="flex items-center gap-2">
                    <CalendarRange class="h-4 w-4 text-sky-600" />
                    <p class="text-sm font-semibold text-foreground">最近活动</p>
                  </div>
                  <p class="mt-3 text-sm font-medium text-foreground">{{ latestTimelineEvent?.title ?? '暂无事件' }}</p>
                  <p class="mt-1 text-xs text-muted-foreground">{{ formatTimestamp(latestTimelineEvent?.committed_at) }}</p>
                  <p class="mt-2 text-[11px] text-muted-foreground">{{ latestTimelineEvent ? getMemorySourceLabel(latestTimelineEvent.source) : '暂无来源' }}</p>
                </div>
              </div>

              <div
                v-if="failedEvents.length"
                class="rounded-[22px] border border-rose-200 bg-rose-50 px-4 py-4 text-sm text-rose-900"
              >
                <div class="flex items-center gap-2">
                  <AlertTriangle class="h-4 w-4" />
                  <p class="font-semibold">当前会话存在失败事件</p>
                </div>
                <p class="mt-2 text-rose-800/80">
                  {{ failedEvents.map((event) => event.title).join('；') }}
                </p>
              </div>

              <Tabs v-model="detailTab" class="space-y-4">
                <TabsList class="grid w-full grid-cols-3">
                  <TabsTrigger value="timeline">操作批次</TabsTrigger>
                  <TabsTrigger value="semantic">语义视图</TabsTrigger>
                  <TabsTrigger value="entity">实体视图</TabsTrigger>
                </TabsList>

                <TabsContent value="timeline" class="space-y-4">
                  <div v-if="!operationGroups.length" class="rounded-2xl border border-dashed border-border/70 bg-muted/10 px-4 py-10 text-center text-sm text-muted-foreground">
                    该 session 暂无结构化记忆事件。
                  </div>

                  <div v-else class="space-y-4">
                    <article
                      v-for="group in operationGroups"
                      :key="group.id"
                      class="rounded-[24px] border border-border/70 bg-muted/10 p-4"
                    >
                      <div class="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
                        <div>
                          <div class="flex flex-wrap items-center gap-2">
                            <Badge variant="secondary" class="text-[10px]">{{ group.label }}</Badge>
                            <Badge class="border text-[10px]" :class="statusBadgeClass(group.status)">{{ group.status }}</Badge>
                            <Badge
                              v-if="group.semanticState !== 'absent'"
                              class="border text-[10px]"
                              :class="getSummaryLifecycleDescriptor(group.semanticState).badgeTone"
                            >
                              {{ getSummaryLifecycleDescriptor(group.semanticState).label }}
                            </Badge>
                          </div>
                          <p class="mt-3 text-sm font-semibold text-foreground">
                            {{ group.events[0]?.title ?? group.label }}
                          </p>
                          <p class="mt-1 text-xs text-muted-foreground">
                            {{ formatTimestamp(group.startedAt) }}
                            <span v-if="group.startedAt !== group.endedAt"> → {{ formatTimestamp(group.endedAt) }}</span>
                          </p>
                        </div>

                        <div class="grid grid-cols-2 gap-2 text-xs lg:min-w-[180px]">
                          <div class="rounded-xl border border-border/60 bg-background/80 px-3 py-2">
                            <p class="text-muted-foreground">事件数</p>
                            <p class="mt-1 font-semibold text-foreground">{{ group.events.length }}</p>
                          </div>
                          <div class="rounded-xl border border-border/60 bg-background/80 px-3 py-2">
                            <p class="text-muted-foreground">来源</p>
                            <p class="mt-1 font-semibold text-foreground">{{ group.source }}</p>
                          </div>
                        </div>
                      </div>

                      <div class="mt-4 space-y-3">
                        <article
                          v-for="event in group.events"
                          :key="event.event_id"
                          class="rounded-2xl border border-border/70 bg-background/90 p-3"
                        >
                          <div class="flex flex-wrap items-center gap-2">
                            <Badge class="border text-[10px]" :class="layerBadgeClass(event.memory_layer)">{{ event.memory_layer }}</Badge>
                            <Badge variant="outline" class="text-[10px] font-mono">{{ event.action }}</Badge>
                            <Badge v-if="event.display_kind" variant="secondary" class="text-[10px] font-mono">
                              {{ event.display_kind }}
                            </Badge>
                            <Badge class="border text-[10px]" :class="statusBadgeClass(event.status)">{{ event.status }}</Badge>
                          </div>
                          <p class="mt-2 text-sm font-medium text-foreground">{{ event.title }}</p>
                          <p v-if="event.reason" class="mt-1 text-xs leading-5 text-muted-foreground">{{ event.reason }}</p>
                          <p class="mt-2 text-[11px] text-muted-foreground">
                            {{ getMemorySourceLabel(event.source) }}
                            <span v-if="event.source_turn"> · Turn {{ event.source_turn }}</span>
                            <span v-if="event.memory_key"> · {{ event.memory_key }}</span>
                            <span> · {{ formatTimestamp(event.committed_at) }}</span>
                          </p>

                          <div v-if="event.before || event.after" class="mt-3 grid gap-3 lg:grid-cols-2">
                            <div v-if="event.before" class="rounded-xl border border-border/70 bg-muted/20 p-3">
                              <p class="mb-2 text-[10px] font-semibold uppercase tracking-wide text-muted-foreground">Before</p>
                              <div class="space-y-1">
                                <p
                                  v-for="field in formatMemoryPayloadFields(event.before)"
                                  :key="`before-${event.event_id}-${field.label}`"
                                  class="text-[11px] leading-5 text-foreground"
                                >
                                  <span class="font-medium text-muted-foreground">{{ field.label }}：</span>{{ field.value }}
                                </p>
                              </div>
                              <details class="mt-3">
                                <summary class="cursor-pointer text-[10px] font-medium uppercase tracking-wide text-muted-foreground">原始 JSON</summary>
                                <pre class="mt-2 overflow-x-auto whitespace-pre-wrap text-[11px] leading-5 text-muted-foreground">{{ stringifyPayload(event.before) }}</pre>
                              </details>
                            </div>
                            <div v-if="event.after" class="rounded-xl border border-border/70 bg-muted/20 p-3">
                              <p class="mb-2 text-[10px] font-semibold uppercase tracking-wide text-muted-foreground">After</p>
                              <div class="space-y-1">
                                <p
                                  v-for="field in formatMemoryPayloadFields(event.after)"
                                  :key="`after-${event.event_id}-${field.label}`"
                                  class="text-[11px] leading-5 text-foreground"
                                >
                                  <span class="font-medium text-muted-foreground">{{ field.label }}：</span>{{ field.value }}
                                </p>
                              </div>
                              <details class="mt-3">
                                <summary class="cursor-pointer text-[10px] font-medium uppercase tracking-wide text-muted-foreground">原始 JSON</summary>
                                <pre class="mt-2 overflow-x-auto whitespace-pre-wrap text-[11px] leading-5 text-muted-foreground">{{ stringifyPayload(event.after) }}</pre>
                              </details>
                            </div>
                          </div>
                        </article>
                      </div>
                    </article>
                  </div>
                </TabsContent>

                <TabsContent value="semantic" class="space-y-4">
                  <div class="grid gap-4 lg:grid-cols-[minmax(0,1.15fr)_minmax(280px,0.85fr)]">
                    <div class="rounded-[24px] border border-violet-200/70 bg-violet-50/50 p-4">
                      <div class="flex items-center justify-between gap-3">
                        <div>
                          <p class="text-sm font-semibold text-violet-900">当前摘要状态</p>
                          <p class="mt-1 text-xs leading-5 text-violet-900/75">
                            {{ summaryStateLabel(effectiveTimelineResponse.summary_state.state) }}
                          </p>
                        </div>
                        <Badge class="border text-[10px]" :class="detailSummaryDescriptor.badgeTone">
                          {{ effectiveTimelineResponse.summary_state.state }}
                        </Badge>
                      </div>

                      <div v-if="effectiveTimelineResponse.summary_state.current_summary" class="mt-4 space-y-3">
                        <div class="rounded-2xl border border-violet-200/70 bg-white/80 px-4 py-3">
                          <p class="text-sm leading-6 text-foreground">{{ effectiveTimelineResponse.summary_state.current_summary.summary_text }}</p>
                        </div>
                        <div v-if="effectiveTimelineResponse.summary_state.current_summary.key_facts?.length" class="flex flex-wrap gap-1.5">
                          <Badge
                            v-for="fact in effectiveTimelineResponse.summary_state.current_summary.key_facts.slice(0, 10)"
                            :key="fact"
                            variant="secondary"
                            class="text-[10px] font-normal"
                          >
                            {{ fact }}
                          </Badge>
                        </div>
                      </div>

                      <p v-else class="mt-4 text-sm text-violet-900/75">
                        当前没有可用摘要，可能尚未生成，或最近一次操作已将其 reset。
                      </p>
                    </div>

                    <div class="rounded-[24px] border border-border/70 bg-muted/10 p-4">
                      <div class="flex items-center gap-2">
                        <TimerReset class="h-4 w-4 text-sky-600" />
                        <p class="text-sm font-semibold text-foreground">最近语义事件</p>
                      </div>
                      <div v-if="effectiveTimelineResponse.summary_state.last_semantic_event" class="mt-4 space-y-2">
                        <div class="flex flex-wrap items-center gap-2">
                          <Badge class="border text-[10px]" :class="layerBadgeClass('semantic')">semantic</Badge>
                          <Badge variant="outline" class="text-[10px] font-mono">
                            {{ effectiveTimelineResponse.summary_state.last_semantic_event.action }}
                          </Badge>
                          <Badge
                            v-if="effectiveTimelineResponse.summary_state.last_semantic_event.display_kind"
                            variant="secondary"
                            class="text-[10px] font-mono"
                          >
                            {{ effectiveTimelineResponse.summary_state.last_semantic_event.display_kind }}
                          </Badge>
                        </div>
                        <p class="text-sm font-medium text-foreground">{{ effectiveTimelineResponse.summary_state.last_semantic_event.title }}</p>
                        <p v-if="effectiveTimelineResponse.summary_state.last_semantic_event.reason" class="text-xs leading-5 text-muted-foreground">
                          {{ effectiveTimelineResponse.summary_state.last_semantic_event.reason }}
                        </p>
                        <p class="text-[11px] text-muted-foreground">
                          {{ formatTimestamp(effectiveTimelineResponse.summary_state.last_semantic_event.committed_at) }}
                        </p>
                      </div>
                      <p v-else class="mt-4 text-sm text-muted-foreground">当前 session 还没有语义层事件。</p>
                    </div>
                  </div>

                  <div v-if="!semanticEvents.length" class="rounded-2xl border border-dashed border-border/70 bg-muted/10 px-4 py-10 text-center text-sm text-muted-foreground">
                    当前 session 还没有 semantic 事件。
                  </div>

                  <div v-else class="space-y-3">
                    <article
                      v-for="event in semanticEvents"
                      :key="event.event_id"
                      class="rounded-[22px] border border-border/70 bg-muted/10 p-4"
                    >
                      <div class="flex flex-wrap items-center gap-2">
                        <Badge class="border text-[10px]" :class="layerBadgeClass('semantic')">semantic</Badge>
                        <Badge variant="outline" class="text-[10px] font-mono">{{ event.action }}</Badge>
                        <Badge v-if="event.display_kind" variant="secondary" class="text-[10px] font-mono">
                          {{ event.display_kind }}
                        </Badge>
                        <Badge class="border text-[10px]" :class="statusBadgeClass(event.status)">{{ event.status }}</Badge>
                      </div>
                      <p class="mt-3 text-sm font-semibold text-foreground">{{ event.title }}</p>
                      <p v-if="event.reason" class="mt-1 text-xs leading-5 text-muted-foreground">{{ event.reason }}</p>
                      <p class="mt-2 text-[11px] text-muted-foreground">
                        {{ getMemorySourceLabel(event.source) }}
                        <span v-if="event.memory_key"> · {{ event.memory_key }}</span>
                        <span> · {{ formatTimestamp(event.committed_at) }}</span>
                      </p>
                    </article>
                  </div>
                </TabsContent>

                <TabsContent value="entity" class="space-y-4">
                  <div class="grid gap-4 lg:grid-cols-[minmax(0,1.15fr)_minmax(280px,0.85fr)]">
                    <div class="rounded-[24px] border border-orange-200/70 bg-[linear-gradient(180deg,rgba(255,247,237,0.92),rgba(255,255,255,0.95))] p-4">
                      <div class="flex items-center justify-between gap-3">
                        <div>
                          <p class="text-sm font-semibold text-orange-950">当前实体快照</p>
                          <p class="mt-1 text-xs leading-5 text-orange-900/75">
                            按角色查看地点、状态标签、携带物与最近证据，作为当前故事事实层的前端快照。
                          </p>
                        </div>
                        <Badge class="border border-orange-200 bg-white/85 text-[10px] text-orange-700">
                          {{ selectedEntitySnapshot?.total ?? 0 }} 人
                        </Badge>
                      </div>

                      <div v-if="selectedEntitySnapshot?.items?.length" class="mt-4 space-y-3">
                        <article
                          v-for="entity in selectedEntitySnapshot.items"
                          :key="entity.entity_id"
                          class="rounded-[20px] border border-orange-200/60 bg-white/80 p-4"
                        >
                          <div class="flex items-start justify-between gap-3">
                            <div class="min-w-0">
                              <p class="truncate text-sm font-semibold text-foreground">{{ entity.display_name }}</p>
                              <p class="mt-1 text-[11px] uppercase tracking-wide text-muted-foreground">
                                {{ entity.current_location || '位置待确认' }}
                              </p>
                            </div>
                            <Badge variant="outline" class="bg-white/85 text-[10px] font-mono">
                              {{ formatTimestamp(entity.updated_at) }}
                            </Badge>
                          </div>

                          <div class="mt-3 space-y-3">
                            <p class="rounded-xl border border-orange-100 bg-orange-50/60 px-3 py-2 text-[11px] leading-5 text-foreground">
                              {{ entity.state_summary || '当前还没有压缩后的实体摘要。' }}
                            </p>

                            <div v-if="entity.status_tags.length" class="flex flex-wrap gap-1.5">
                              <Badge
                                v-for="tag in entity.status_tags"
                                :key="`${entity.entity_id}-${tag}`"
                                class="border border-orange-200 bg-white/85 text-[10px] text-orange-800"
                              >
                                {{ tag }}
                              </Badge>
                            </div>

                            <div v-if="entity.inventory.length" class="flex items-start gap-2 text-[11px] text-foreground">
                              <Package class="mt-0.5 h-3.5 w-3.5 shrink-0 text-orange-600" />
                              <span class="leading-5">{{ entity.inventory.join('、') }}</span>
                            </div>

                            <div v-if="entity.companions.length" class="flex items-start gap-2 text-[11px] text-foreground">
                              <Users class="mt-0.5 h-3.5 w-3.5 shrink-0 text-sky-600" />
                              <span class="leading-5">{{ entity.companions.map((item) => resolveEntityCompanionLabel(item)).join('、') }}</span>
                            </div>

                            <div v-if="entity.evidence.length" class="rounded-xl border border-border/60 bg-muted/10 px-3 py-2">
                              <p class="text-[10px] uppercase tracking-wide text-muted-foreground">最近证据</p>
                              <p class="mt-2 text-[11px] leading-5 text-foreground">{{ entity.evidence[0] }}</p>
                            </div>
                          </div>
                        </article>
                      </div>

                      <div v-else class="mt-4 rounded-2xl border border-dashed border-orange-200 bg-white/70 px-4 py-10 text-center text-sm text-orange-900/75">
                        当前 session 还没有已缓存的实体状态快照。
                      </div>
                    </div>

                    <div class="space-y-4">
                      <div class="rounded-[24px] border border-violet-200/70 bg-violet-50/40 p-4">
                        <div class="flex items-center gap-2">
                          <Sparkles class="h-4 w-4 text-violet-600" />
                          <p class="text-sm font-semibold text-foreground">结构化 world update</p>
                        </div>
                        <div v-if="selectedWorldUpdateHighlights.length" class="mt-4 space-y-2">
                          <p
                            v-for="line in selectedWorldUpdateHighlights"
                            :key="line"
                            class="rounded-xl border border-violet-200/70 bg-white/80 px-3 py-2 text-[11px] leading-5 text-foreground"
                          >
                            {{ line }}
                          </p>
                        </div>
                        <p v-else class="mt-4 text-sm text-muted-foreground">
                          当前 session 还没有缓存到结构化 world update。
                        </p>
                      </div>

                      <div class="rounded-[24px] border border-border/70 bg-muted/10 p-4">
                        <div class="flex items-center gap-2">
                          <MapPinned class="h-4 w-4 text-orange-600" />
                          <p class="text-sm font-semibold text-foreground">实体追踪提示</p>
                        </div>
                        <div class="mt-4 space-y-2">
                          <p
                            v-for="warning in selectedEntityWarnings"
                            :key="warning"
                            class="rounded-xl border border-border/70 bg-background/80 px-3 py-2 text-[11px] leading-5 text-foreground"
                          >
                            {{ warning }}
                          </p>
                        </div>
                      </div>

                      <div class="rounded-[24px] border border-border/70 bg-muted/10 p-4">
                        <div class="flex items-center gap-2">
                          <History class="h-4 w-4 text-orange-600" />
                          <p class="text-sm font-semibold text-foreground">实体事件</p>
                        </div>
                        <div v-if="entityEvents.length" class="mt-4 space-y-3">
                          <article
                            v-for="event in entityEvents"
                            :key="event.event_id"
                            class="rounded-2xl border border-border/70 bg-background/80 p-3"
                          >
                            <div class="flex flex-wrap items-center gap-2">
                              <Badge class="border text-[10px]" :class="layerBadgeClass('entity_state')">entity_state</Badge>
                              <Badge variant="outline" class="text-[10px] font-mono">{{ event.action }}</Badge>
                              <Badge class="border text-[10px]" :class="statusBadgeClass(event.status)">{{ event.status }}</Badge>
                            </div>
                            <p class="mt-2 text-sm font-medium text-foreground">{{ event.title }}</p>
                            <p v-if="event.reason" class="mt-1 text-xs leading-5 text-muted-foreground">{{ event.reason }}</p>
                            <p class="mt-2 text-[11px] text-muted-foreground">
                              {{ getMemorySourceLabel(event.source) }}
                              <span v-if="event.memory_key"> · {{ event.memory_key }}</span>
                              <span> · {{ formatTimestamp(event.committed_at) }}</span>
                            </p>
                          </article>
                        </div>
                        <p v-else class="mt-4 text-sm text-muted-foreground">当前 session 还没有 entity_state 事件。</p>
                      </div>

                      <div class="rounded-[24px] border border-emerald-200/70 bg-emerald-50/40 p-4">
                        <div class="flex items-center gap-2">
                          <Sparkles class="h-4 w-4 text-emerald-600" />
                          <p class="text-sm font-semibold text-foreground">字段级 patch 时间线</p>
                        </div>
                        <div v-if="selectedEntityPatchUpdates.length" class="mt-4 space-y-3">
                          <article
                            v-for="patch in selectedEntityPatchUpdates"
                            :key="getEntityPatchEventId(patch)"
                            class="rounded-2xl border border-emerald-200/70 bg-white/80 p-3"
                          >
                            <div class="flex flex-wrap items-center gap-2">
                              <Badge class="border text-[10px]" :class="layerBadgeClass('entity_state')">entity_patch</Badge>
                              <Badge variant="outline" class="text-[10px] font-mono">{{ patch.op }}</Badge>
                              <Badge v-if="patch.sequence !== null" variant="secondary" class="text-[10px] font-mono">
                                seq {{ patch.sequence }}
                              </Badge>
                              <Badge class="border text-[10px]" :class="statusBadgeClass(patch.status)">{{ patch.status }}</Badge>
                            </div>
                            <p class="mt-2 text-sm font-medium text-foreground">{{ getEntityPatchHeadline(patch) }}</p>
                            <p class="mt-1 text-xs leading-5 text-muted-foreground">{{ getEntityPatchDetail(patch) }}</p>
                            <p class="mt-2 text-[11px] text-muted-foreground">
                              {{ getMemorySourceLabel(patch.source) }}
                              <span v-if="getEntityPatchSourceTurn(patch)"> · Turn {{ getEntityPatchSourceTurn(patch) }}</span>
                              <span> · {{ formatTimestamp(getEntityPatchCommittedAt(patch)) }}</span>
                            </p>
                            <p v-if="getEntityPatchEvidenceText(patch)" class="mt-2 text-[11px] leading-5 text-foreground/80">
                              证据：{{ getEntityPatchEvidenceText(patch) }}
                            </p>
                          </article>
                        </div>
                        <p v-else class="mt-4 text-sm text-muted-foreground">当前 session 还没有字段级 entity patch 记录。</p>
                      </div>
                    </div>
                  </div>
                </TabsContent>
              </Tabs>
            </div>
          </CardContent>
        </Card>
      </section>
    </div>
  </div>
</template>
