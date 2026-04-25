/**
 * 文件说明：把故事段与记忆事件组装成“按轮次查看”的展示模型。
 */

import type { MemoryUpdateTimelineItem } from '@/domains/memory/api/memoryUpdatesApi'
import type { StoredStory, StorySegment } from '@/components/story/types'

export interface StoryMemoryRoundView {
  id: string
  turn: number | null
  prompt: string
  timestamp?: string | null
  creationModeLabel: string
  contextLabels: string[]
  designLabels: string[]
  events: MemoryUpdateTimelineItem[]
  status: 'committed' | 'failed' | 'stale'
  missingSegment: boolean
}

export interface StoryMemoryRoundCollection {
  storyId?: string | null
  storyTitle: string
  worldId?: string | null
  worldName?: string | null
  rounds: StoryMemoryRoundView[]
  unassignedEvents: MemoryUpdateTimelineItem[]
}

function compactIdentifier(value: string, maxLength = 18) {
  const normalized = value.trim()
  if (normalized.length <= maxLength) return normalized
  return `${normalized.slice(0, 8)}…${normalized.slice(-6)}`
}

function getEventStatus(events: MemoryUpdateTimelineItem[]): 'committed' | 'failed' | 'stale' {
  if (events.some((event) => event.status === 'failed')) return 'failed'
  if (events.some((event) => event.status === 'stale')) return 'stale'
  return 'committed'
}

function getCreationModeLabel(segment: StorySegment | null, runtimeSnapshot: Record<string, unknown> | null) {
  const runtimeMode = typeof runtimeSnapshot?.creation_mode === 'string' ? runtimeSnapshot.creation_mode : null
  const mode = runtimeMode ?? segment?.creation_mode ?? null
  if (mode === 'scripted') return '严格剧本'
  if (mode === 'improv') return '渐进创作'
  return '历史轮次'
}

function collectDesignLabels(
  story: StoredStory,
  segment: StorySegment | null,
): string[] {
  const labels = new Set<string>()
  const runtimeSnapshot = (
    segment?.runtime_state_snapshot && typeof segment.runtime_state_snapshot === 'object'
      ? segment.runtime_state_snapshot
      : null
  ) as Record<string, unknown> | null
  const metadata = (
    story.metadata && typeof story.metadata === 'object'
      ? story.metadata
      : {}
  ) as Record<string, unknown>

  if (segment?.retrieved_context?.length) {
    segment.retrieved_context
      .map((item) => item.trim())
      .filter(Boolean)
      .slice(0, 4)
      .forEach((item) => labels.add(item))
  }

  const followScriptDesign = runtimeSnapshot?.creation_mode === 'scripted' || metadata.follow_script_design === true
  if (followScriptDesign) labels.add('跟随剧本设计')

  const scriptDesignId = typeof runtimeSnapshot?.script_design_id === 'string'
    ? runtimeSnapshot.script_design_id
    : (typeof metadata.script_design_id === 'string' ? metadata.script_design_id : '')
  if (scriptDesignId) labels.add(`剧本 ${compactIdentifier(scriptDesignId)}`)

  const stageId = typeof runtimeSnapshot?.current_stage_id === 'string'
    ? runtimeSnapshot.current_stage_id
    : (typeof metadata.active_stage_id === 'string' ? metadata.active_stage_id : '')
  if (stageId) labels.add(`阶段 ${compactIdentifier(stageId)}`)

  const eventId = typeof runtimeSnapshot?.current_event_id === 'string'
    ? runtimeSnapshot.current_event_id
    : (typeof metadata.active_event_id === 'string' ? metadata.active_event_id : '')
  if (eventId) labels.add(`事件 ${compactIdentifier(eventId)}`)

  return Array.from(labels)
}

function sortEventsDesc(events: MemoryUpdateTimelineItem[]) {
  return [...events].sort((left, right) => {
    const timeCompare = right.committed_at.localeCompare(left.committed_at)
    if (timeCompare !== 0) return timeCompare
    return (right.sequence ?? 0) - (left.sequence ?? 0)
  })
}

export function buildStoryMemoryRounds(args: {
  story: StoredStory | null | undefined
  events: MemoryUpdateTimelineItem[]
}): StoryMemoryRoundCollection | null {
  const story = args.story
  if (!story) return null

  const turnGroups = new Map<number, MemoryUpdateTimelineItem[]>()
  const unassignedEvents: MemoryUpdateTimelineItem[] = []

  for (const event of args.events) {
    const turn = typeof event.source_turn === 'number' && event.source_turn > 0
      ? event.source_turn
      : null
    if (!turn) {
      unassignedEvents.push(event)
      continue
    }
    const bucket = turnGroups.get(turn) ?? []
    bucket.push(event)
    turnGroups.set(turn, bucket)
  }

  const rounds = Array.from(turnGroups.entries())
    .sort((left, right) => right[0] - left[0])
    .map(([turn, items]) => {
      const segment = story.segments[turn - 1] ?? null
      const runtimeSnapshot = (
        segment?.runtime_state_snapshot && typeof segment.runtime_state_snapshot === 'object'
          ? segment.runtime_state_snapshot
          : null
      ) as Record<string, unknown> | null
      return {
        id: `${story.id}-turn-${turn}`,
        turn,
        prompt: segment?.prompt?.trim() || '该轮 prompt 已不可用',
        timestamp: segment?.timestamp ?? items[0]?.committed_at ?? null,
        creationModeLabel: getCreationModeLabel(segment, runtimeSnapshot),
        contextLabels: segment?.retrieved_context?.filter((item) => item.trim()).slice(0, 4) ?? [],
        designLabels: collectDesignLabels(story, segment),
        events: sortEventsDesc(items),
        status: getEventStatus(items),
        missingSegment: segment == null,
      } satisfies StoryMemoryRoundView
    })

  return {
    storyId: story.id,
    storyTitle: story.title,
    worldId: story.world_id,
    worldName: story.world_name,
    rounds,
    unassignedEvents: sortEventsDesc(unassignedEvents),
  }
}
