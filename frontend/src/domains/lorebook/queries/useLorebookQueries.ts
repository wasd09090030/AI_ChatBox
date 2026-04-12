/**
 * TanStack Query hooks for Worlds & Lorebook Entries
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/vue-query'
import type { MaybeRef } from 'vue'
import { computed, unref } from 'vue'
import {
  worldApi,
  lorebookApi,
  type WorldCreate,
  type WorldUpdate,
  type CharacterEntryCreate,
  type LocationEntryCreate,
  type EventEntryCreate,
  type UpdateEntryPayload,
  type BulkImportEntry,
} from '@/services/lorebookService'

// 变量作用：变量 LOREBOOK_KEYS，用于 LOREBOOK KEYS 相关配置或状态。
export const LOREBOOK_KEYS = {
  worlds: ['worlds'] as const,
  world: (id: string) => ['worlds', id] as const,
  entries: (worldId?: string) => ['lorebook', 'entries', worldId ?? 'all'] as const,
}

// ── Worlds ─────────────────────────────────────────────────────────────────

export function useWorldsQuery() {
  return useQuery({
    queryKey: LOREBOOK_KEYS.worlds,
    queryFn: () => worldApi.list(),
  })
}

/** 功能：函数 useCreateWorldMutation，负责 useCreateWorldMutation 相关处理。 */
export function useCreateWorldMutation() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: WorldCreate) => worldApi.create(data),
    onSuccess: () => qc.invalidateQueries({ queryKey: LOREBOOK_KEYS.worlds }),
  })
}

/** 功能：函数 useUpdateWorldMutation，负责 useUpdateWorldMutation 相关处理。 */
export function useUpdateWorldMutation() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: WorldUpdate }) =>
      worldApi.update(id, data),
    onSuccess: () => qc.invalidateQueries({ queryKey: LOREBOOK_KEYS.worlds }),
  })
}

/** 功能：函数 useDeleteWorldMutation，负责 useDeleteWorldMutation 相关处理。 */
export function useDeleteWorldMutation() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => worldApi.delete(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: LOREBOOK_KEYS.worlds }),
  })
}

// ── Lorebook Entries ────────────────────────────────────────────────────────

export function useLorebookEntriesQuery(worldId?: MaybeRef<string | undefined>) {
  return useQuery({
    // Reactive queryKey: re-evaluates whenever worldId changes
    queryKey: computed(() => LOREBOOK_KEYS.entries(unref(worldId) || undefined)),
    queryFn: () => lorebookApi.listEntries(unref(worldId)),
    enabled: computed(() => !!unref(worldId)),
  })
}

/** 功能：函数 useAddCharacterMutation，负责 useAddCharacterMutation 相关处理。 */
export function useAddCharacterMutation(worldId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: CharacterEntryCreate) => lorebookApi.addCharacter(worldId, data),
    onSuccess: () => qc.invalidateQueries({ queryKey: LOREBOOK_KEYS.entries(worldId) }),
  })
}

/** 功能：函数 useAddLocationMutation，负责 useAddLocationMutation 相关处理。 */
export function useAddLocationMutation(worldId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: LocationEntryCreate) => lorebookApi.addLocation(worldId, data),
    onSuccess: () => qc.invalidateQueries({ queryKey: LOREBOOK_KEYS.entries(worldId) }),
  })
}

/** 功能：函数 useAddEventMutation，负责 useAddEventMutation 相关处理。 */
export function useAddEventMutation(worldId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: EventEntryCreate) => lorebookApi.addEvent(worldId, data),
    onSuccess: () => qc.invalidateQueries({ queryKey: LOREBOOK_KEYS.entries(worldId) }),
  })
}

/** 功能：函数 useUpdateEntryMutation，负责 useUpdateEntryMutation 相关处理。 */
export function useUpdateEntryMutation() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ entryId, payload }: { entryId: string; payload: UpdateEntryPayload }) =>
      lorebookApi.updateEntry(entryId, payload),
    onSuccess: (_data, vars) =>
      qc.invalidateQueries({ queryKey: LOREBOOK_KEYS.entries(vars.payload.world_id) }),
  })
}

/** 功能：函数 useDeleteEntryMutation，负责 useDeleteEntryMutation 相关处理。 */
export function useDeleteEntryMutation(worldId?: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (entryId: string) => lorebookApi.deleteEntry(entryId),
    onSuccess: () =>
      qc.invalidateQueries({ queryKey: LOREBOOK_KEYS.entries(worldId) }),
  })
}

/** 功能：函数 useBulkImportMutation，负责 useBulkImportMutation 相关处理。 */
export function useBulkImportMutation() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ worldId, entries }: { worldId: string; entries: BulkImportEntry[] }) =>
      lorebookApi.bulkImport(worldId, entries),
    onSuccess: (_data, vars) =>
      qc.invalidateQueries({ queryKey: LOREBOOK_KEYS.entries(vars.worldId) }),
  })
}



