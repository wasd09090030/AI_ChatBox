/**
 * 文件说明：前端业务域逻辑与接口封装。
 */

import type {
  EntityStateCollection,
  EntityStateUpdate,
  MemoryUpdateEvent,
  StoryMemoryPayload,
  SummaryMemorySnapshot,
} from '@/domains/story/api/storyGenerationApi'

/** ????? sortMemoryUpdatesDesc??? sortMemoryUpdatesDesc ????? */
function sortMemoryUpdatesDesc<T extends { committed_at: string; sequence?: number | null }>(items: T[]): T[] {
  return [...items].sort((left, right) => {
    const timeCompare = right.committed_at.localeCompare(left.committed_at)
    if (timeCompare !== 0) return timeCompare
    return (right.sequence ?? 0) - (left.sequence ?? 0)
  })
}

/** 功能：函数 getStoryMemorySummarySnapshot，负责 getStoryMemorySummarySnapshot 相关处理。 */
export function getStoryMemorySummarySnapshot(
  storyMemory: StoryMemoryPayload | null | undefined,
): SummaryMemorySnapshot | null {
  return storyMemory?.semantic?.summary_memory_snapshot ?? null
}

/** 功能：函数 getStoryMemoryEntitySnapshot，负责 getStoryMemoryEntitySnapshot 相关处理。 */
export function getStoryMemoryEntitySnapshot(
  storyMemory: StoryMemoryPayload | null | undefined,
): EntityStateCollection | null {
  return storyMemory?.entity?.entity_state_snapshot ?? null
}

/** 功能：函数 getStoryMemoryEntityUpdates，负责 getStoryMemoryEntityUpdates 相关处理。 */
export function getStoryMemoryEntityUpdates(
  storyMemory: StoryMemoryPayload | null | undefined,
  limit = 30,
): EntityStateUpdate[] {
  return sortMemoryUpdatesDesc(storyMemory?.entity?.entity_state_updates ?? []).slice(0, limit)
}

/** 功能：函数 getStoryMemoryWorldUpdate，负责 getStoryMemoryWorldUpdate 相关处理。 */
export function getStoryMemoryWorldUpdate(
  storyMemory: StoryMemoryPayload | null | undefined,
): Record<string, unknown> | null {
  return storyMemory?.entity?.world_update ?? null
}

/** 功能：函数 getStoryMemoryTimelineEvents，负责 getStoryMemoryTimelineEvents 相关处理。 */
export function getStoryMemoryTimelineEvents(
  storyMemory: StoryMemoryPayload | null | undefined,
  limit = 50,
): MemoryUpdateEvent[] {
  return sortMemoryUpdatesDesc(storyMemory?.timeline?.memory_updates ?? []).slice(0, limit)
}
