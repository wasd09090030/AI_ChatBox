/**
 * 文件说明：前端业务域逻辑与接口封装。
 */

import { useQuery } from '@tanstack/vue-query'
import { computed, unref, type MaybeRef } from 'vue'
import {
  getMemoryUpdates,
  getSessionMemoryTimeline,
  getSessionStoryMemory,
  type MemoryUpdateQueryFilters,
} from '@/domains/memory/api/memoryUpdatesApi'

// 变量作用：变量 MEMORY_UPDATE_KEYS，用于 MEMORY UPDATE KEYS 相关配置或状态。
export const MEMORY_UPDATE_KEYS = {
  all: ['memory-updates'] as const,
  list: (filtersKey: string) => ['memory-updates', 'list', filtersKey] as const,
  session: (sessionId: string, page: number, pageSize: number) =>
    ['memory-updates', 'session', sessionId, page, pageSize] as const,
  storyMemory: (sessionId: string, page: number, pageSize: number, storyId: string) =>
    ['memory-updates', 'story-memory', sessionId, page, pageSize, storyId] as const,
}

/** 功能：函数 createFiltersKey，负责 createFiltersKey 相关处理。 */
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

/** 功能：函数 useMemoryUpdatesQuery，负责 useMemoryUpdatesQuery 相关处理。 */
export function useMemoryUpdatesQuery(filters: MaybeRef<MemoryUpdateQueryFilters>) {
  return useQuery({
    queryKey: computed(() => MEMORY_UPDATE_KEYS.list(createFiltersKey(unref(filters)))),
    queryFn: () => getMemoryUpdates(unref(filters)),
    refetchInterval: 30000,
  })
}

/** 功能：函数 useSessionMemoryTimelineQuery，负责 useSessionMemoryTimelineQuery 相关处理。 */
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

/** 功能：函数 useSessionStoryMemoryQuery，负责 useSessionStoryMemoryQuery 相关处理。 */
export function useSessionStoryMemoryQuery(
  sessionId: MaybeRef<string | null | undefined>,
  page: MaybeRef<number> = 1,
  pageSize: MaybeRef<number> = 100,
  storyId: MaybeRef<string | null | undefined> = null,
) {
  return useQuery({
    queryKey: computed(() => MEMORY_UPDATE_KEYS.storyMemory(
      unref(sessionId) || 'none',
      unref(page),
      unref(pageSize),
      unref(storyId) || 'none',
    )),
    queryFn: () => getSessionStoryMemory(
      unref(sessionId) || '',
      unref(page),
      unref(pageSize),
      unref(storyId),
    ),
    enabled: computed(() => !!unref(sessionId)),
    refetchInterval: 30000,
  })
}
