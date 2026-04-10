import type {
  EntityStateCollection,
  EntityStateUpdate,
  MemoryUpdateEvent,
  StoryMemoryPayload,
  SummaryMemorySnapshot,
} from '@/domains/story/api/storyGenerationApi'

function sortMemoryUpdatesDesc<T extends { committed_at: string; sequence?: number | null }>(items: T[]): T[] {
  return [...items].sort((left, right) => {
    const timeCompare = right.committed_at.localeCompare(left.committed_at)
    if (timeCompare !== 0) return timeCompare
    return (right.sequence ?? 0) - (left.sequence ?? 0)
  })
}

export function getStoryMemorySummarySnapshot(
  storyMemory: StoryMemoryPayload | null | undefined,
): SummaryMemorySnapshot | null {
  return storyMemory?.semantic?.summary_memory_snapshot ?? null
}

export function getStoryMemoryEntitySnapshot(
  storyMemory: StoryMemoryPayload | null | undefined,
): EntityStateCollection | null {
  return storyMemory?.entity?.entity_state_snapshot ?? null
}

export function getStoryMemoryEntityUpdates(
  storyMemory: StoryMemoryPayload | null | undefined,
  limit = 30,
): EntityStateUpdate[] {
  return sortMemoryUpdatesDesc(storyMemory?.entity?.entity_state_updates ?? []).slice(0, limit)
}

export function getStoryMemoryWorldUpdate(
  storyMemory: StoryMemoryPayload | null | undefined,
): Record<string, unknown> | null {
  return storyMemory?.entity?.world_update ?? null
}

export function getStoryMemoryTimelineEvents(
  storyMemory: StoryMemoryPayload | null | undefined,
  limit = 50,
): MemoryUpdateEvent[] {
  return sortMemoryUpdatesDesc(storyMemory?.timeline?.memory_updates ?? []).slice(0, limit)
}
