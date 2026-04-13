/**
 * 文件说明：前端业务域逻辑与接口封装。
 */

import type { MemoryUpdateEvent, SummaryMemorySnapshot } from '@/domains/story/api/storyGenerationApi'

export type SummaryLifecycleState = 'absent' | 'created' | 'reset' | 'recreated' | 'stale'

export interface SummaryLifecycleDescriptor {
  state: SummaryLifecycleState
  label: string
  description: string
  tone: string
  badgeTone: string
}

export interface MemoryPayloadField {
  label: string
  value: string
}

export interface MemoryOperationGroup<TEvent extends MemoryUpdateEvent = MemoryUpdateEvent> {
  id: string
  source: string
  label: string
  startedAt: string
  endedAt: string
  events: TEvent[]
  semanticState: SummaryLifecycleState
  status: 'committed' | 'failed' | 'stale'
}

// 常量 OPERATION_WINDOW_MS。
const OPERATION_WINDOW_MS = 5000

const MEMORY_LAYER_LABELS: Record<string, string> = {
  episodic: '剧情记录',
  semantic: '摘要记忆',
  entity_state: '实体状态',
  profile: '角色画像',
  procedural: '流程记忆',
  system: '系统记录',
}

const MEMORY_ACTION_LABELS: Record<string, string> = {
  created: '已创建',
  merged: '已合并',
  updated: '已更新',
  reset: '已重置',
  reindexed: '已重建索引',
  superseded: '已被替换',
  marked_stale: '已标记过期',
  rebuilt: '已重建',
}

function sortEventsAsc<TEvent extends Pick<MemoryUpdateEvent, 'committed_at'>>(events: TEvent[]): TEvent[] {
  return [...events].sort((a, b) => a.committed_at.localeCompare(b.committed_at))
}

/** ????? sortEventsWithinOperation??? sortEventsWithinOperation ????? */
function sortEventsWithinOperation<TEvent extends MemoryUpdateEvent>(events: TEvent[]): TEvent[] {
  return [...events].sort((a, b) => {
    const aSequence = typeof a.sequence === 'number' ? a.sequence : Number.MAX_SAFE_INTEGER
    const bSequence = typeof b.sequence === 'number' ? b.sequence : Number.MAX_SAFE_INTEGER
    if (a.operation_id && b.operation_id && a.operation_id === b.operation_id && aSequence !== bSequence) {
      return aSequence - bSequence
    }
    if (a.committed_at !== b.committed_at) {
      return a.committed_at.localeCompare(b.committed_at)
    }
    return a.event_id.localeCompare(b.event_id)
  })
}

/** 处理 deriveSummaryLifecycleState 相关逻辑。 */
export function deriveSummaryLifecycleState(
  events: Pick<MemoryUpdateEvent, 'memory_layer' | 'action' | 'status' | 'committed_at'>[],
  currentSummary?: SummaryMemorySnapshot | null,
): SummaryLifecycleState {
  const semanticEvents = sortEventsAsc(events.filter((event) => event.memory_layer === 'semantic'))
  const hasSummary = Boolean(currentSummary)
  const hasReset = semanticEvents.some((event) => event.action === 'reset')
  const hasCreated = semanticEvents.some((event) => event.action === 'created')
  const hasStale = semanticEvents.some((event) => event.action === 'marked_stale' || event.status === 'stale')
  const hasMerged = semanticEvents.some((event) => event.action === 'merged' || event.action === 'updated')

  if (hasSummary && hasReset && hasCreated) return 'recreated'
  if (!hasSummary && hasReset) return 'reset'
  if (hasSummary && hasStale) return 'stale'
  if (hasSummary && (hasCreated || hasMerged)) return 'created'
  if (hasSummary) return 'created'
  return 'absent'
}

/** 处理 getSummaryLifecycleDescriptor 相关逻辑。 */
export function getSummaryLifecycleDescriptor(
  state: SummaryLifecycleState,
  options?: {
    scope?: 'story' | 'dashboard'
    reason?: string | null
  },
): SummaryLifecycleDescriptor {
  const scope = options?.scope ?? 'dashboard'
  const fallbackResetReason = scope === 'story'
    ? '本轮显式移除了已有摘要，后续生成后才会重建。'
    : '该会话的摘要已被显式移除，当前没有可用语义摘要。'

  switch (state) {
    case 'recreated':
      return {
        state,
        label: '摘要已重建',
        description: scope === 'story'
          ? '本轮先重置旧摘要，再基于新上下文完成了语义重建。'
          : '该会话经历 reset 后又重新生成了新的摘要，语义链路闭环完整。',
        tone: 'border-emerald-200 bg-emerald-50 text-emerald-900',
        badgeTone: 'border-emerald-200 bg-emerald-50 text-emerald-700',
      }
    case 'reset':
      return {
        state,
        label: '摘要已重置',
        description: options?.reason?.trim() || fallbackResetReason,
        tone: 'border-amber-200 bg-amber-50 text-amber-900',
        badgeTone: 'border-amber-200 bg-amber-50 text-amber-700',
      }
    case 'stale':
      return {
        state,
        label: '摘要已过期',
        description: scope === 'story'
          ? '摘要暂时保留，但当前内容已不再可靠，建议等待后续刷新。'
          : '该会话存在摘要，但最近事件已将其标记为 stale，需要重新刷新或重建。',
        tone: 'border-yellow-200 bg-yellow-50 text-yellow-900',
        badgeTone: 'border-yellow-200 bg-yellow-50 text-yellow-700',
      }
    case 'created':
      return {
        state,
        label: scope === 'story' ? '摘要保持有效' : '摘要已创建',
        description: scope === 'story'
          ? '当前摘要可继续作为后续上下文压缩结果使用。'
          : '该会话已有可用摘要，最近的语义写入已经完成。',
        tone: 'border-violet-200 bg-violet-50 text-violet-900',
        badgeTone: 'border-violet-200 bg-violet-50 text-violet-700',
      }
    case 'absent':
    default:
      return {
        state: 'absent',
        label: '尚未生成摘要',
        description: scope === 'story'
          ? '对话轮次或触发条件尚未达到摘要生成阈值。'
          : '该会话目前没有任何可用摘要，通常表示尚未触发语义压缩。',
        tone: 'border-slate-200 bg-slate-50 text-slate-800',
        badgeTone: 'border-slate-200 bg-slate-50 text-slate-600',
      }
  }
}

/** 处理 getMemorySourceLabel 相关逻辑。 */
export function getMemorySourceLabel(source: string): string {
  switch (source) {
    case 'generate':
      return '生成写入'
    case 'rollback':
      return '回滚修复'
    case 'regenerate':
      return '重生成修复'
    case 'story_adjustment_commit':
      return '正文调整提交'
    default:
      return source || '未知来源'
  }
}

/** 处理 getMemoryLayerLabel 相关逻辑。 */
export function getMemoryLayerLabel(layer: string): string {
  return MEMORY_LAYER_LABELS[layer] ?? (layer || '未知层级')
}

/** 处理 getMemoryActionLabel 相关逻辑。 */
export function getMemoryActionLabel(action: string): string {
  return MEMORY_ACTION_LABELS[action] ?? (action || '未知动作')
}

/** 处理 getMemoryStatusLabel 相关逻辑。 */
export function getMemoryStatusLabel(status?: string | null): string {
  switch (status) {
    case 'failed':
      return '失败'
    case 'stale':
      return '已过期'
    case 'committed':
    default:
      return '正常'
  }
}

/** 处理 formatMemoryPayloadFields 相关逻辑。 */
export function formatMemoryPayloadFields(payload?: Record<string, unknown> | null): MemoryPayloadField[] {
  if (!payload) return []

  const fields: MemoryPayloadField[] = []
  if (typeof payload.summary_text === 'string' && payload.summary_text.trim()) {
    fields.push({ label: '摘要', value: payload.summary_text.trim() })
  }
  if (Array.isArray(payload.key_facts) && payload.key_facts.length) {
    fields.push({
      label: '事实',
      value: payload.key_facts
        .map((item) => String(item).trim())
        .filter(Boolean)
        .slice(0, 8)
        .join(' / '),
    })
  }
  if (typeof payload.last_turn === 'number') {
    fields.push({ label: '轮次', value: String(payload.last_turn) })
  }
  if (typeof payload.message_count === 'number') {
    fields.push({ label: '消息数', value: String(payload.message_count) })
  }
  if (typeof payload.indexed_message_count === 'number') {
    fields.push({ label: '索引消息数', value: String(payload.indexed_message_count) })
  }
  if (typeof payload.memory_key === 'string' && payload.memory_key.trim()) {
    fields.push({ label: 'Key', value: payload.memory_key.trim() })
  }

  if (fields.length) return fields

  return [
    {
      label: 'Payload',
      value: JSON.stringify(payload),
    },
  ]
}

/** ????? groupMemoryEventsByOperation??? groupMemoryEventsByOperation ????? */
export function groupMemoryEventsByOperation<TEvent extends MemoryUpdateEvent>(events: TEvent[]): MemoryOperationGroup<TEvent>[] {
  if (!events.length) return []

  const withOperationId = events.every((event) => typeof event.operation_id === 'string' && event.operation_id.trim())
  if (withOperationId) {
    const grouped = new Map<string, TEvent[]>()
    for (const event of events) {
      const operationId = String(event.operation_id)
      const bucket = grouped.get(operationId) ?? []
      bucket.push(event)
      grouped.set(operationId, bucket)
    }

    return Array.from(grouped.entries())
      .map(([operationId, operationEvents]) => {
        const sortedEvents = sortEventsWithinOperation(operationEvents)
        const headEvent = sortedEvents[0]
        const semanticTail = [...sortedEvents].reverse().find((event) => event.memory_layer === 'semantic')
        const semanticState = deriveSummaryLifecycleState(
          sortedEvents,
          semanticTail?.after
            ? ({
                summary_text: typeof semanticTail.after.summary_text === 'string' ? semanticTail.after.summary_text : '',
                key_facts: Array.isArray(semanticTail.after.key_facts)
                  ? semanticTail.after.key_facts.map((item) => String(item))
                  : [],
                last_turn: typeof semanticTail.after.last_turn === 'number' ? semanticTail.after.last_turn : undefined,
              } satisfies SummaryMemorySnapshot)
            : null,
        )
        const hasFailed = sortedEvents.some((event) => event.status === 'failed')
        const hasStale = sortedEvents.some((event) => event.status === 'stale')

        return {
          id: operationId,
          source: headEvent?.source ?? 'unknown',
          label: getMemorySourceLabel(headEvent?.source ?? 'unknown'),
          startedAt: sortedEvents[0]?.committed_at ?? '',
          endedAt: sortedEvents[sortedEvents.length - 1]?.committed_at ?? '',
          events: sortedEvents,
          semanticState,
          status: hasFailed ? 'failed' : hasStale ? 'stale' : 'committed',
        } satisfies MemoryOperationGroup<TEvent>
      })
      .sort((a, b) => b.endedAt.localeCompare(a.endedAt))
  }

  const sortedDesc = [...events].sort((a, b) => b.committed_at.localeCompare(a.committed_at))
  const groups: MemoryOperationGroup<TEvent>[] = []

  for (const event of sortedDesc) {
    const latestGroup = groups[groups.length - 1]
    const latestGroupStartedAt = latestGroup ? new Date(latestGroup.startedAt).getTime() : 0
    const currentTime = new Date(event.committed_at).getTime()

    if (
      latestGroup
      && latestGroup.source === event.source
      && Number.isFinite(currentTime)
      && Number.isFinite(latestGroupStartedAt)
      && Math.abs(latestGroupStartedAt - currentTime) <= OPERATION_WINDOW_MS
    ) {
      latestGroup.events.push(event)
      latestGroup.endedAt = latestGroup.events[0]?.committed_at ?? latestGroup.endedAt
      latestGroup.startedAt = latestGroup.events[latestGroup.events.length - 1]?.committed_at ?? latestGroup.startedAt
      continue
    }

    groups.push({
      id: `${event.source}-${event.event_id}`,
      source: event.source,
      label: getMemorySourceLabel(event.source),
      startedAt: event.committed_at,
      endedAt: event.committed_at,
      events: [event],
      semanticState: 'absent',
      status: event.status === 'failed' ? 'failed' : event.status === 'stale' ? 'stale' : 'committed',
    })
  }

  return groups.map((group) => {
    const sortedEvents = sortEventsAsc(group.events)
    const semanticTail = [...sortedEvents].reverse().find((event) => event.memory_layer === 'semantic')
    const semanticState = deriveSummaryLifecycleState(
      sortedEvents,
      semanticTail?.after
        ? ({
            summary_text: typeof semanticTail.after.summary_text === 'string' ? semanticTail.after.summary_text : '',
            key_facts: Array.isArray(semanticTail.after.key_facts)
              ? semanticTail.after.key_facts.map((item) => String(item))
              : [],
            last_turn: typeof semanticTail.after.last_turn === 'number' ? semanticTail.after.last_turn : undefined,
          } satisfies SummaryMemorySnapshot)
        : null,
    )
    const hasFailed = group.events.some((event) => event.status === 'failed')
    const hasStale = group.events.some((event) => event.status === 'stale')

    return {
      ...group,
      events: sortedEvents,
      semanticState,
      status: hasFailed ? 'failed' : hasStale ? 'stale' : 'committed',
      startedAt: sortedEvents[0]?.committed_at ?? group.startedAt,
      endedAt: sortedEvents[sortedEvents.length - 1]?.committed_at ?? group.endedAt,
    }
  })
}
