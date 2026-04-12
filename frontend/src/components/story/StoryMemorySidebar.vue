<script setup lang="ts">
// 文件说明：前端可复用界面组件。
import { computed } from 'vue'
import {
  AlertTriangle,
  Brain,
  FlagTriangleRight,
  History,
  Info,
  ListOrdered,
  MapPinned,
  Milestone,
  Package,
  Route,
  Sparkles,
  Users,
} from 'lucide-vue-next'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { ScrollArea } from '@/components/ui/scroll-area'
import type {
  EntityStateCollection,
  EntityStateSnapshot,
  EntityStateUpdate,
  MemoryUpdateEvent,
  SummaryMemorySnapshot,
} from '@/domains/story/api/storyGenerationApi'
import {
  extractWorldUpdateHighlights,
  getEntityPatchCommittedAt,
  getEntityPatchDetail,
  getEntityPatchEvidenceText,
  getEntityPatchEventId,
  getEntityPatchHeadline,
  getEntityPatchSourceTurn,
} from '@/domains/story/entityPatchPresentation'
import type { StoryEntityUpdateRecord, StoryWorldUpdateRecord } from '@/stores/storySession'
import {
  deriveSummaryLifecycleState,
  formatMemoryPayloadFields,
  getSummaryLifecycleDescriptor,
} from '@/domains/memory/memoryUpdatePresentation'

interface StoryContextHit {
  label: string
  detail: string
  source: 'explicit' | 'rag' | 'rule'
}

interface StorySummaryDiff {
  summaryChanged: boolean
  newFacts: string[]
  removedFacts: string[]
  previousLastTurn: number | null
  currentLastTurn: number | null
}

// 变量作用：变量 props，用于 props 相关配置或状态。
const props = withDefaults(
  defineProps<{
    showScriptProgress?: boolean
    scriptDesignTitle?: string | null
    activeStageTitle?: string | null
    activeEventTitle?: string | null
    followScriptDesign?: boolean
    canAdvanceEvent?: boolean
    canAdvanceStage?: boolean
    progressUpdating?: boolean
    lastSummary: SummaryMemorySnapshot | null
    lastSummaryDiff?: StorySummaryDiff | null
    lastContexts?: StoryContextHit[]
    lastMemoryUpdates?: MemoryUpdateEvent[]
    lastEntityState?: EntityStateCollection | null
    lastEntityStateUpdates?: Array<EntityStateUpdate | StoryEntityUpdateRecord>
    lastWorldUpdate?: Record<string, unknown> | StoryWorldUpdateRecord | null
  }>(),
  {
    showScriptProgress: true,
    scriptDesignTitle: null,
    activeStageTitle: null,
    activeEventTitle: null,
    followScriptDesign: false,
    canAdvanceEvent: false,
    canAdvanceStage: false,
    progressUpdating: false,
    lastSummaryDiff: null,
    lastContexts: () => [],
    lastMemoryUpdates: () => [],
    lastEntityState: null,
    lastEntityStateUpdates: () => [],
    lastWorldUpdate: null,
  },
)

// 变量作用：变量 emit，用于 emit 相关配置或状态。
const emit = defineEmits<{
  (event: 'save-progress'): void
  (event: 'advance-event'): void
  (event: 'advance-stage'): void
}>()

// 变量作用：变量 orderedEvents，用于 orderedEvents 相关配置或状态。
const orderedEvents = computed(() => [...props.lastMemoryUpdates].sort((a, b) => a.committed_at.localeCompare(b.committed_at)))
// 变量作用：变量 semanticEvents，用于 semanticEvents 相关配置或状态。
const semanticEvents = computed(() => props.lastMemoryUpdates.filter((event) => event.memory_layer === 'semantic'))
// 变量作用：变量 episodicEvents，用于 episodicEvents 相关配置或状态。
const episodicEvents = computed(() => props.lastMemoryUpdates.filter((event) => event.memory_layer === 'episodic'))
// 变量作用：变量 entityEvents，用于 entityEvents 相关配置或状态。
const entityEvents = computed(() => props.lastMemoryUpdates.filter((event) => event.memory_layer === 'entity_state'))
// 变量作用：变量 failedEvents，用于 failedEvents 相关配置或状态。
const failedEvents = computed(() => props.lastMemoryUpdates.filter((event) => event.status === 'failed'))
// 变量作用：变量 orderedEntityItems，用于 orderedEntityItems 相关配置或状态。
const orderedEntityItems = computed(() => [...(props.lastEntityState?.items ?? [])].sort((a, b) => a.display_name.localeCompare(b.display_name, 'zh-CN')))
// 变量作用：变量 entityNameMap，用于 entityNameMap 相关配置或状态。
const entityNameMap = computed(() => new Map(orderedEntityItems.value.map((item) => [item.entity_id, item.display_name])))
// 变量作用：变量 entityLocationCount，用于 entityLocationCount 相关配置或状态。
const entityLocationCount = computed(() => new Set(orderedEntityItems.value.map((item) => item.current_location).filter(Boolean)).size)
// 变量作用：变量 latestEntityEvent，用于 latestEntityEvent 相关配置或状态。
const latestEntityEvent = computed(() => (
  [...entityEvents.value].reverse().find(Boolean) ?? null
))

// 变量作用：变量 latestSemanticEvent，用于 latestSemanticEvent 相关配置或状态。
const latestSemanticEvent = computed(() => (
  [...semanticEvents.value].reverse().find(Boolean) ?? null
))

// 变量作用：变量 latestEpisodicEvent，用于 latestEpisodicEvent 相关配置或状态。
const latestEpisodicEvent = computed(() => (
  [...episodicEvents.value].reverse().find(Boolean) ?? null
))

// 变量作用：变量 summaryState，用于 summaryState 相关配置或状态。
const summaryState = computed(() => deriveSummaryLifecycleState(props.lastMemoryUpdates, props.lastSummary))
// 变量作用：变量 summaryLifecycle，用于 summaryLifecycle 相关配置或状态。
const summaryLifecycle = computed(() => {
  if (props.lastSummary && !semanticEvents.value.length) {
    return {
      label: '摘要保持有效',
      tone: 'border-slate-200 bg-slate-50 text-slate-700',
      description: '本轮没有新的语义写入，当前摘要继续作为已压缩上下文使用。',
    }
  }
  return getSummaryLifecycleDescriptor(summaryState.value, {
    scope: 'story',
    reason: latestSemanticEvent.value?.reason,
  })
})

// 变量作用：变量 episodicLifecycle，用于 episodicLifecycle 相关配置或状态。
const episodicLifecycle = computed(() => {
  if (!latestEpisodicEvent.value) {
    return '本轮未记录 episodic 维护动作。'
  }
  if (latestEpisodicEvent.value.action === 'reindexed' || latestEpisodicEvent.value.action === 'rebuilt') {
    return '本轮已执行会话重建或历史索引修复。'
  }
  return '本轮主要更新原始会话消息与历史索引。'
})

// 变量作用：变量 entityWarnings，用于 entityWarnings 相关配置或状态。
const entityWarnings = computed(() => {
  const warnings: string[] = []
  if (!orderedEntityItems.value.length) {
    warnings.push('当前故事还没有稳定的角色实体快照，说明这一轮尚未形成可追踪人物事实。')
    return warnings
  }

  const missingLocation = orderedEntityItems.value.filter((item) => !item.current_location)
  if (missingLocation.length) {
    warnings.push(`这些角色仍缺少明确地点：${missingLocation.slice(0, 3).map((item) => item.display_name).join('、')}`)
  }

  const missingEvidence = orderedEntityItems.value.filter((item) => !item.evidence.length)
  if (missingEvidence.length) {
    warnings.push(`这些角色状态还没有文本证据：${missingEvidence.slice(0, 3).map((item) => item.display_name).join('、')}`)
  }

  const unresolvedCompanions = orderedEntityItems.value
    .flatMap((item) => item.companions.map((companionId) => ({ owner: item.display_name, companionId })))
    .filter((item) => !entityNameMap.value.has(item.companionId))
  if (unresolvedCompanions.length) {
    warnings.push(`同行关系中仍有未解析引用，最近一条来自：${unresolvedCompanions[0]?.owner ?? '未知角色'}`)
  }

  return warnings.slice(0, 3)
})
// 变量作用：变量 latestEntityPatch，用于 latestEntityPatch 相关配置或状态。
const latestEntityPatch = computed(() => props.lastEntityStateUpdates[0] ?? null)
// 变量作用：变量 orderedEntityPatches，用于 orderedEntityPatches 相关配置或状态。
const orderedEntityPatches = computed(() => [...props.lastEntityStateUpdates].slice(0, 8))
// 变量作用：变量 worldUpdateHighlights，用于 worldUpdateHighlights 相关配置或状态。
const worldUpdateHighlights = computed(() => extractWorldUpdateHighlights(props.lastWorldUpdate))

/** 功能：函数 formatEntityUpdatedAt，负责 formatEntityUpdatedAt 相关处理。 */
function formatEntityUpdatedAt(value?: string | null) {
  if (!value) return '未知时间'
  try {
    return new Date(value).toLocaleTimeString('zh-CN', {
      hour: '2-digit',
      minute: '2-digit',
    })
  } catch {
    return value
  }
}

/** 功能：函数 resolveCompanionLabel，负责 resolveCompanionLabel 相关处理。 */
function resolveCompanionLabel(companionId: string) {
  return entityNameMap.value.get(companionId) ?? companionId
}

/** 功能：函数 entityTone，负责 entityTone 相关处理。 */
function entityTone(entity: EntityStateSnapshot) {
  if (entity.status_tags.includes('昏迷')) return 'border-rose-300 bg-rose-50/80'
  if (entity.status_tags.includes('受伤')) return 'border-amber-300 bg-amber-50/80'
  if (entity.status_tags.includes('警觉')) return 'border-sky-300 bg-sky-50/80'
  return 'border-stone-200 bg-stone-50/80'
}
</script>

<template>
  <aside class="w-72 border-l border-border flex flex-col shrink-0">
    <ScrollArea class="flex-1">
      <div v-if="showScriptProgress" class="px-4 pt-4 pb-3 border-b border-border">
        <p class="text-sm font-semibold flex items-center gap-1.5 mb-0.5">
          <Route class="h-3.5 w-3.5 text-emerald-600" />
          剧本推进
        </p>
        <p class="text-xs text-muted-foreground mb-2">显式确认当前故事的主线阶段与事件推进。</p>

        <div class="space-y-2 rounded-lg border border-emerald-200/70 bg-emerald-50/60 px-3 py-3 text-xs">
          <div class="flex items-center justify-between gap-2">
            <span class="text-muted-foreground">剧本状态</span>
            <Badge :variant="followScriptDesign ? 'default' : 'secondary'" class="text-[10px]">
              {{ followScriptDesign ? '跟随中' : '未跟随' }}
            </Badge>
          </div>

          <div>
            <p class="text-[10px] text-muted-foreground mb-1">当前剧本</p>
            <p class="font-medium text-foreground">{{ scriptDesignTitle || '未绑定剧本设计' }}</p>
          </div>

          <div class="rounded-md bg-white/80 px-2.5 py-2 border border-emerald-100">
            <p class="text-[10px] text-muted-foreground flex items-center gap-1 mb-1">
              <Milestone class="h-3 w-3" />当前阶段
            </p>
            <p class="text-foreground">{{ activeStageTitle || '未指定' }}</p>
          </div>

          <div class="rounded-md bg-white/80 px-2.5 py-2 border border-emerald-100">
            <p class="text-[10px] text-muted-foreground flex items-center gap-1 mb-1">
              <FlagTriangleRight class="h-3 w-3" />当前事件
            </p>
            <p class="text-foreground">{{ activeEventTitle || '未指定' }}</p>
          </div>

          <div class="grid grid-cols-1 gap-2 pt-1">
            <Button size="sm" class="h-8 text-xs" :disabled="progressUpdating || !scriptDesignTitle" @click="emit('save-progress')">
              保存当前推进
            </Button>
            <Button size="sm" variant="outline" class="h-8 text-xs" :disabled="progressUpdating || !canAdvanceEvent" @click="emit('advance-event')">
              推进到下一事件
            </Button>
            <Button size="sm" variant="outline" class="h-8 text-xs" :disabled="progressUpdating || !canAdvanceStage" @click="emit('advance-stage')">
              推进到下一阶段
            </Button>
          </div>
        </div>
      </div>

      <div class="px-4 pt-4 pb-3 border-b border-border">
        <p class="text-sm font-semibold flex items-center gap-1.5 mb-0.5">
          <Sparkles class="h-3.5 w-3.5 text-amber-500" />
          本轮故事记忆
        </p>
        <p class="text-xs text-muted-foreground mb-2">把本轮生成、回滚或重生成后的故事记忆变化翻译成可读结论。</p>

        <div class="space-y-3">
          <div
            v-if="failedEvents.length"
            class="rounded-lg border border-rose-200 bg-rose-50 px-3 py-3 text-xs text-rose-900"
          >
            <div class="flex items-center justify-between gap-2">
              <p class="font-medium flex items-center gap-1.5">
                <AlertTriangle class="h-3.5 w-3.5" />
                记忆修复存在失败
              </p>
              <Badge variant="outline" class="border-rose-200 bg-white text-[10px] text-rose-700">
                {{ failedEvents.length }} 条失败
              </Badge>
            </div>
            <p class="mt-2 leading-relaxed">
              {{ failedEvents.map((event) => event.title).join('；') }}
            </p>
          </div>

          <div class="rounded-lg border px-3 py-3 text-xs" :class="summaryLifecycle.tone">
            <div class="flex items-center justify-between gap-2">
              <p class="font-medium">{{ summaryLifecycle.label }}</p>
              <Badge variant="outline" class="text-[10px] font-mono">
                {{ summaryState }}
              </Badge>
            </div>
            <p class="mt-2 leading-relaxed">{{ summaryLifecycle.description }}</p>
          </div>

          <div class="rounded-lg border border-sky-200/70 bg-sky-50/60 px-3 py-3 text-xs text-sky-900">
            <div class="flex items-center justify-between gap-2">
              <p class="font-medium">Episodic 维护结果</p>
              <Badge variant="outline" class="text-[10px] font-mono">
                {{ latestEpisodicEvent?.action ?? 'none' }}
              </Badge>
            </div>
            <p class="mt-2 leading-relaxed">{{ episodicLifecycle }}</p>
          </div>
        </div>
      </div>

      <div class="px-4 pt-4 pb-3 border-b border-border">
        <p class="text-sm font-semibold flex items-center gap-1.5 mb-0.5">
          <MapPinned class="h-3.5 w-3.5 text-orange-600" />
          实体态势板
        </p>
        <p class="text-xs text-muted-foreground mb-2">把本轮故事中的主要人物状态压缩成当前战术视图。</p>

        <div class="space-y-3">
          <div class="grid grid-cols-3 gap-2">
            <div class="rounded-xl border border-orange-200/70 bg-orange-50/80 px-3 py-2">
              <p class="text-[10px] uppercase tracking-wide text-orange-700/80">角色数</p>
              <p class="mt-1 text-sm font-semibold text-orange-950">{{ orderedEntityItems.length }}</p>
            </div>
            <div class="rounded-xl border border-sky-200/70 bg-sky-50/80 px-3 py-2">
              <p class="text-[10px] uppercase tracking-wide text-sky-700/80">地点数</p>
              <p class="mt-1 text-sm font-semibold text-sky-950">{{ entityLocationCount }}</p>
            </div>
            <div class="rounded-xl border border-stone-200/70 bg-stone-50/80 px-3 py-2">
              <p class="text-[10px] uppercase tracking-wide text-stone-600">本轮事件</p>
              <p class="mt-1 text-sm font-semibold text-stone-900">{{ entityEvents.length }}</p>
            </div>
          </div>

          <div
            v-if="entityWarnings.length"
            class="rounded-xl border border-amber-200/80 bg-[linear-gradient(135deg,rgba(255,247,237,0.96),rgba(255,255,255,0.9))] px-3 py-3"
          >
            <div class="flex items-center gap-2">
              <AlertTriangle class="h-3.5 w-3.5 text-amber-600" />
              <p class="text-xs font-semibold uppercase tracking-wide text-amber-700">追踪提示</p>
            </div>
            <div class="mt-2 space-y-2">
              <p
                v-for="warning in entityWarnings"
                :key="warning"
                class="text-[11px] leading-relaxed text-amber-950"
              >
                {{ warning }}
              </p>
            </div>
          </div>

          <div v-if="orderedEntityItems.length" class="space-y-2">
            <article
              v-for="entity in orderedEntityItems.slice(0, 6)"
              :key="entity.entity_id"
              class="rounded-[18px] border px-3 py-3 shadow-[0_1px_0_rgba(255,255,255,0.65)_inset]"
              :class="entityTone(entity)"
            >
              <div class="flex items-start justify-between gap-3">
                <div class="min-w-0">
                  <p class="truncate text-sm font-semibold text-foreground">{{ entity.display_name }}</p>
                  <p class="mt-1 text-[10px] uppercase tracking-[0.18em] text-muted-foreground">
                    {{ entity.current_location || '位置待确认' }}
                  </p>
                </div>
                <Badge variant="outline" class="shrink-0 bg-white/80 text-[10px] font-mono">
                  {{ formatEntityUpdatedAt(entity.updated_at) }}
                </Badge>
              </div>

              <div class="mt-3 space-y-2">
                <div class="flex items-start gap-2 text-[11px] text-foreground">
                  <MapPinned class="mt-0.5 h-3.5 w-3.5 shrink-0 text-orange-600" />
                  <span class="leading-relaxed">{{ entity.state_summary || '当前还没有压缩摘要。' }}</span>
                </div>

                <div v-if="entity.status_tags.length" class="flex flex-wrap gap-1">
                  <Badge
                    v-for="tag in entity.status_tags"
                    :key="`${entity.entity_id}-${tag}`"
                    class="border border-white/80 bg-white/80 text-[10px] text-foreground"
                  >
                    {{ tag }}
                  </Badge>
                </div>

                <div v-if="entity.inventory.length" class="flex items-start gap-2 text-[11px] text-foreground">
                  <Package class="mt-0.5 h-3.5 w-3.5 shrink-0 text-stone-600" />
                  <span class="leading-relaxed">{{ entity.inventory.join('、') }}</span>
                </div>

                <div v-if="entity.companions.length" class="flex items-start gap-2 text-[11px] text-foreground">
                  <Users class="mt-0.5 h-3.5 w-3.5 shrink-0 text-sky-600" />
                  <span class="leading-relaxed">
                    {{ entity.companions.map((item) => resolveCompanionLabel(item)).join('、') }}
                  </span>
                </div>

                <p v-if="entity.short_goal" class="rounded-xl border border-white/70 bg-white/70 px-2.5 py-2 text-[11px] leading-relaxed text-foreground">
                  目标：{{ entity.short_goal }}
                </p>

                <details v-if="entity.evidence.length" class="rounded-xl border border-white/70 bg-white/65 px-2.5 py-2">
                  <summary class="cursor-pointer text-[10px] font-medium uppercase tracking-wide text-muted-foreground">
                    最近证据
                  </summary>
                  <div class="mt-2 space-y-2">
                    <p
                      v-for="evidence in entity.evidence.slice(0, 2)"
                      :key="`${entity.entity_id}-${evidence}`"
                      class="text-[11px] leading-relaxed text-foreground"
                    >
                      {{ evidence }}
                    </p>
                  </div>
                </details>
              </div>
            </article>
          </div>

          <div v-else class="rounded-xl border border-dashed border-border bg-muted/15 px-3 py-4 text-xs text-muted-foreground">
            当前 session 还没有可展示的实体状态快照。
          </div>

          <div
            v-if="latestEntityEvent"
            class="rounded-xl border border-sky-200/70 bg-[linear-gradient(135deg,rgba(240,249,255,0.96),rgba(255,255,255,0.9))] px-3 py-3 text-xs"
          >
            <div class="flex items-center justify-between gap-2">
              <p class="font-medium text-sky-950">最近实体事件</p>
              <Badge variant="outline" class="bg-white/80 text-[10px] font-mono">
                {{ latestEntityEvent.action }}
              </Badge>
            </div>
            <p class="mt-2 leading-relaxed text-foreground">{{ latestEntityEvent.title }}</p>
            <p v-if="latestEntityEvent.reason" class="mt-1 leading-relaxed text-muted-foreground">{{ latestEntityEvent.reason }}</p>
          </div>

          <div
            v-if="lastWorldUpdate"
            class="rounded-xl border border-violet-200/70 bg-[linear-gradient(135deg,rgba(245,243,255,0.96),rgba(255,255,255,0.92))] px-3 py-3 text-xs"
          >
            <div class="flex items-center justify-between gap-2">
              <p class="font-medium text-violet-950">结构化 world update</p>
              <Badge variant="outline" class="bg-white/80 text-[10px] font-mono">
                {{ lastWorldUpdate.operationId || 'n/a' }}
              </Badge>
            </div>
            <div class="mt-2 space-y-2">
              <p
                v-for="line in worldUpdateHighlights"
                :key="line"
                class="leading-relaxed text-foreground"
              >
                {{ line }}
              </p>
            </div>
          </div>

          <div class="rounded-xl border border-emerald-200/70 bg-emerald-50/60 px-3 py-3 text-xs">
            <div class="flex items-center justify-between gap-2">
              <p class="font-medium text-emerald-950">字段级 patch 时间线</p>
              <Badge variant="outline" class="bg-white/80 text-[10px] font-mono">
                {{ orderedEntityPatches.length }} 条
              </Badge>
            </div>
            <p v-if="latestEntityPatch" class="mt-2 leading-relaxed text-muted-foreground">
              最近一条：{{ getEntityPatchHeadline(latestEntityPatch) }}
            </p>
            <div v-if="orderedEntityPatches.length" class="mt-3 space-y-2">
              <article
                v-for="patch in orderedEntityPatches"
                :key="getEntityPatchEventId(patch)"
                class="rounded-lg border border-emerald-200/70 bg-white/80 px-3 py-2.5"
              >
                <div class="flex items-start justify-between gap-2">
                  <div class="min-w-0">
                    <p class="text-[11px] font-medium text-foreground">{{ getEntityPatchHeadline(patch) }}</p>
                    <p class="mt-1 text-[11px] leading-relaxed text-muted-foreground">{{ getEntityPatchDetail(patch) }}</p>
                  </div>
                  <Badge variant="outline" class="shrink-0 text-[10px] font-mono">
                    {{ patch.sequence ?? '-' }}
                  </Badge>
                </div>
                <p class="mt-2 text-[10px] text-muted-foreground">
                  {{ patch.source }}
                  <span v-if="getEntityPatchSourceTurn(patch)"> · Turn {{ getEntityPatchSourceTurn(patch) }}</span>
                  <span> · {{ formatEntityUpdatedAt(getEntityPatchCommittedAt(patch)) }}</span>
                </p>
                <p v-if="getEntityPatchEvidenceText(patch)" class="mt-1 text-[10px] leading-relaxed text-foreground/80">
                  证据：{{ getEntityPatchEvidenceText(patch) }}
                </p>
              </article>
            </div>
            <p v-else class="mt-3 italic text-muted-foreground">当前轮次还没有字段级 patch。</p>
          </div>
        </div>
      </div>

      <div class="px-4 pt-4 pb-3 border-b border-border">
        <p class="text-sm font-semibold flex items-center gap-1.5 mb-0.5">
          <Brain class="h-3.5 w-3.5 text-violet-500" />
          摘要记忆
        </p>
        <p class="text-xs text-muted-foreground mb-2">LLM 压缩的历史上下文</p>
        <div v-if="lastSummary" class="space-y-2">
          <div class="rounded-lg bg-violet-500/8 border border-violet-500/20 px-3 py-2 text-xs leading-relaxed text-foreground">
            {{ lastSummary.summary_text }}
          </div>
          <div v-if="lastSummary.key_facts?.length" class="flex flex-wrap gap-1">
            <Badge
              v-for="fact in lastSummary.key_facts.slice(0, 10)"
              :key="fact"
              variant="secondary"
              class="text-[10px]"
            >
              {{ fact }}
            </Badge>
          </div>
          <p class="text-[10px] text-muted-foreground flex items-center gap-1">
            <Info class="h-2.5 w-2.5" />
            第 {{ lastSummary.last_turn }} 轮存档
          </p>
          <div
            v-if="lastSummaryDiff && (lastSummaryDiff.summaryChanged || lastSummaryDiff.newFacts.length || lastSummaryDiff.removedFacts.length)"
            class="rounded-lg border border-violet-200/80 bg-white/70 px-3 py-2"
          >
            <p class="mb-2 text-[10px] font-medium uppercase tracking-wide text-violet-600">Summary Diff</p>
            <p v-if="lastSummaryDiff.summaryChanged" class="text-[11px] text-foreground">摘要文本已变化</p>
            <div v-if="lastSummaryDiff.newFacts.length" class="mt-2">
              <p class="text-[10px] text-emerald-600 mb-1">新增事实</p>
              <div class="flex flex-wrap gap-1">
                <Badge v-for="fact in lastSummaryDiff.newFacts" :key="`new-${fact}`" variant="secondary" class="text-[10px] bg-emerald-500/10 text-emerald-700">
                  {{ fact }}
                </Badge>
              </div>
            </div>
            <div v-if="lastSummaryDiff.removedFacts.length" class="mt-2">
              <p class="text-[10px] text-rose-600 mb-1">移除事实</p>
              <div class="flex flex-wrap gap-1">
                <Badge v-for="fact in lastSummaryDiff.removedFacts" :key="`removed-${fact}`" variant="secondary" class="text-[10px] bg-rose-500/10 text-rose-700">
                  {{ fact }}
                </Badge>
              </div>
            </div>
          </div>
        </div>
        <div v-else class="rounded-lg border border-dashed border-border bg-muted/20 px-3 py-3 text-xs text-muted-foreground">
          <p class="font-medium text-foreground/80">{{ summaryLifecycle.label }}</p>
          <p class="mt-2 leading-relaxed">{{ summaryLifecycle.description }}</p>
        </div>
      </div>

      <div class="px-4 pt-4 pb-3 border-b border-border">
        <p class="text-sm font-semibold flex items-center gap-1.5 mb-0.5">
          <History class="h-3.5 w-3.5 text-sky-600" />
          本轮事件链
        </p>
        <p class="text-xs text-muted-foreground mb-2">按实际写入顺序展示本轮 generate / rollback / regenerate / commit 触发的记忆事件。</p>
        <div v-if="orderedEvents.length" class="space-y-2">
          <div
            v-for="(event, index) in orderedEvents.slice(0, 8)"
            :key="event.event_id"
            class="rounded-lg border border-sky-200/70 bg-sky-50/60 px-3 py-2.5 text-xs"
          >
            <div class="flex items-start gap-3">
              <div class="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full border border-sky-200 bg-white text-[10px] font-semibold text-sky-700">
                {{ index + 1 }}
              </div>
              <div class="min-w-0 flex-1">
                <div class="mb-1 flex items-center justify-between gap-2">
                  <p class="font-medium text-foreground">{{ event.title }}</p>
                  <div class="flex flex-wrap items-center justify-end gap-1">
                    <Badge variant="outline" class="text-[10px] font-mono">
                      {{ event.memory_layer }} / {{ event.action }}
                    </Badge>
                    <Badge v-if="event.display_kind" variant="secondary" class="text-[10px] font-mono">
                      {{ event.display_kind }}
                    </Badge>
                  </div>
                </div>
                <p v-if="event.reason" class="text-muted-foreground leading-relaxed">{{ event.reason }}</p>
                <p class="mt-2 text-[10px] text-muted-foreground">
                  {{ event.source }}
                  <span v-if="event.source_turn"> · Turn {{ event.source_turn }}</span>
                  <span v-if="event.memory_key"> · {{ event.memory_key }}</span>
                  <span v-if="event.status"> · {{ event.status }}</span>
                </p>

                <details v-if="event.before || event.after" class="mt-2 rounded-md border border-white/60 bg-white/70 px-2.5 py-2">
                  <summary class="cursor-pointer text-[10px] font-medium uppercase tracking-wide text-sky-700">
                    展开 before / after
                  </summary>
                  <div class="mt-2 space-y-2">
                    <div v-if="event.before">
                      <p class="text-[10px] uppercase tracking-wide text-muted-foreground">Before</p>
                      <div class="mt-1 space-y-1">
                        <p
                          v-for="field in formatMemoryPayloadFields(event.before)"
                          :key="`before-${event.event_id}-${field.label}`"
                          class="text-[11px] leading-relaxed text-foreground"
                        >
                          <span class="font-medium text-muted-foreground">{{ field.label }}：</span>{{ field.value }}
                        </p>
                      </div>
                    </div>
                    <div v-if="event.after">
                      <p class="text-[10px] uppercase tracking-wide text-muted-foreground">After</p>
                      <div class="mt-1 space-y-1">
                        <p
                          v-for="field in formatMemoryPayloadFields(event.after)"
                          :key="`after-${event.event_id}-${field.label}`"
                          class="text-[11px] leading-relaxed text-foreground"
                        >
                          <span class="font-medium text-muted-foreground">{{ field.label }}：</span>{{ field.value }}
                        </p>
                      </div>
                    </div>
                  </div>
                </details>
              </div>
            </div>
          </div>
        </div>
        <p v-else class="text-xs text-muted-foreground italic">本轮尚未记录结构化记忆更新</p>
      </div>

      <div class="px-4 pt-3 pb-4">
        <p class="text-sm font-semibold flex items-center gap-1.5 mb-0.5">
          <ListOrdered class="h-3.5 w-3.5 text-muted-foreground" />
          命中设定
        </p>
        <p class="text-xs text-muted-foreground mb-2">最近一次生成命中的 Lorebook 条目</p>
        <div class="space-y-2">
          <div
            v-for="(ctx, i) in lastContexts"
            :key="i"
            class="rounded-lg bg-muted/50 px-3 py-2.5 text-xs text-foreground leading-relaxed"
          >
            <div class="mb-1 flex items-center justify-between gap-2">
              <p class="font-medium text-muted-foreground">设定 {{ i + 1 }}</p>
              <Badge :variant="ctx.source === 'explicit' ? 'default' : 'secondary'" class="text-[10px]">
                {{ ctx.label }}
              </Badge>
            </div>
            <p class="line-clamp-5">{{ ctx.detail }}</p>
          </div>
          <p v-if="!lastContexts.length" class="text-xs text-muted-foreground text-center py-4 italic">
            暂无命中设定
          </p>
        </div>
      </div>
    </ScrollArea>
  </aside>
</template>
