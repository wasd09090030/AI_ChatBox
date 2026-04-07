import { useQuery } from '@tanstack/vue-query'
import { computed, unref, type MaybeRef } from 'vue'
import {
  getMemoryUpdates,
  getSessionMemoryTimeline,
  type MemoryUpdateQueryFilters,
} from '@/domains/memory/api/memoryUpdatesApi'

export const MEMORY_UPDATE_KEYS = {
  all: ['memory-updates'] as const,
  list: (filtersKey: string) => ['memory-updates', 'list', filtersKey] as const,
  session: (sessionId: string, page: number, pageSize: number) =>
    ['memory-updates', 'session', sessionId, page, pageSize] as const,
}

function createFiltersKey(filters: MemoryUpdateQueryFilters) {
  return JSON.stringify({
    session_id: filters.session_id ?? '',
    world_id: filters.world_id ?? '',
    source: filters.source ?? '',
    memory_layer: filters.memory_layer ?? '',
    status: filters.status ?? '',
    search: filters.search ?? '',
    date_from: filters.date_from ?? '',
    date_to: filters.date_to ?? '',
    page: filters.page ?? 1,
    page_size: filters.page_size ?? 50,
  })
}

export function useMemoryUpdatesQuery(filters: MaybeRef<MemoryUpdateQueryFilters>) {
  return useQuery({
    queryKey: computed(() => MEMORY_UPDATE_KEYS.list(createFiltersKey(unref(filters)))),
    queryFn: () => getMemoryUpdates(unref(filters)),
    refetchInterval: 30000,
  })
}

export function useSessionMemoryTimelineQuery(
  sessionId: MaybeRef<string | null | undefined>,
  page: MaybeRef<number> = 1,
  pageSize: MaybeRef<number> = 100,
) {
  return useQuery({
    queryKey: computed(() => MEMORY_UPDATE_KEYS.session(unref(sessionId) || 'none', unref(page), unref(pageSize))),
    queryFn: () => getSessionMemoryTimeline(unref(sessionId) || '', unref(page), unref(pageSize)),
    enabled: computed(() => !!unref(sessionId)),
    refetchInterval: 30000,
  })
}
