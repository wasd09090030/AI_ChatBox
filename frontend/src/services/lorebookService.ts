/**
 * Lorebook & World API Service
 */

import apiClient from './api'

// ── Types ─────────────────────────────────────────────────────────────────

export interface World {
  id: string
  name: string
  description: string
  genre: string | null
  setting: string | null
  rules: string | null
  style_preset: string | null
  narrative_tone: string | null
  pacing_style: string | null
  vocabulary_style: string | null
  style_tags: string[]
  default_time_of_day: string | null
  default_weather: string | null
  default_mood: string | null
  metadata: Record<string, unknown>
  created_at: string
  updated_at: string
}

export type WorldCreate = Omit<World, 'id' | 'created_at' | 'updated_at'>
export type WorldUpdate = Partial<WorldCreate>

export type LorebookType = 'character' | 'location' | 'event'

export interface LorebookEntry {
  id: string | null
  world_id: string
  type: LorebookType
  name: string
  description: string
  keywords: string[]
  metadata: Record<string, unknown>
  created_at: string
  updated_at: string
}

// Lorebook entry creation payloads (backend has distinct endpoints per type)
export interface CharacterEntryCreate {
  name: string
  age?: number | null
  gender?: string | null
  appearance?: string | null
  personality?: string | null
  background?: string | null
  speaking_style?: string | null
  role_tier?: 'npc' | 'principal'
  dialogue_enabled?: boolean
  opening_line?: string | null
  example_dialogues?: string[]
  story_function?: string | null
}

export interface LocationEntryCreate {
  name: string
  description: string
  region?: string | null
  climate?: string | null
  mood?: string | null
}

export interface EventEntryCreate {
  name: string
  description: string
  time?: string | null
  location?: string | null
  importance?: number
}

/** Update payload wraps entry_type + world_id + raw data */
export interface UpdateEntryPayload {
  entry_type: LorebookType
  world_id: string
  data: CharacterEntryCreate | LocationEntryCreate | EventEntryCreate
}

/** Bulk import item */
export interface BulkImportEntry {
  entry_type: LorebookType
  data: CharacterEntryCreate | LocationEntryCreate | EventEntryCreate
}

// ── Worlds ─────────────────────────────────────────────────────────────────

export const worldApi = {
  list: (worldId?: string) =>
    apiClient
      .get<World[]>('/worlds', { params: worldId ? { world_id: worldId } : {} })
      .then((r) => r.data),

  get: (id: string) =>
    apiClient.get<World>(`/worlds/${id}`).then((r) => r.data),

  create: (data: WorldCreate) =>
    apiClient.post<World>('/worlds', data).then((r) => r.data),

  update: (id: string, data: WorldUpdate) =>
    apiClient.put<World>(`/worlds/${id}`, data).then((r) => r.data),

  delete: (id: string) =>
    apiClient
      .delete<{ success: boolean; world_id: string }>(`/worlds/${id}`)
      .then((r) => r.data),
}

// ── Lorebook Entries ────────────────────────────────────────────────────────

export const lorebookApi = {
  listEntries: (worldId?: string) =>
    apiClient
      .get<{ entries: LorebookEntry[]; count: number; world_id: string | null }>(
        '/lorebook/entries',
        { params: worldId ? { world_id: worldId } : {} }
      )
      .then((r) => r.data),

  addCharacter: (worldId: string, data: CharacterEntryCreate) =>
    apiClient
      .post<LorebookEntry>(`/worlds/${worldId}/lorebook/character`, data)
      .then((r) => r.data),

  addLocation: (worldId: string, data: LocationEntryCreate) =>
    apiClient
      .post<LorebookEntry>(`/worlds/${worldId}/lorebook/location`, data)
      .then((r) => r.data),

  addEvent: (worldId: string, data: EventEntryCreate) =>
    apiClient
      .post<LorebookEntry>(`/worlds/${worldId}/lorebook/event`, data)
      .then((r) => r.data),

  updateEntry: (entryId: string, payload: UpdateEntryPayload) =>
    apiClient
      .put<{ success: boolean; entry_id: string }>(`/lorebook/entry/${entryId}`, payload)
      .then((r) => r.data),

  deleteEntry: (entryId: string) =>
    apiClient
      .delete<{ success: boolean; entry_id: string }>(`/lorebook/entry/${entryId}`)
      .then((r) => r.data),

  bulkImport: (worldId: string, entries: BulkImportEntry[]) =>
    apiClient
      .post<{ imported: number; failed: number; details: unknown }>(
        `/worlds/${worldId}/lorebook/bulk-import`,
        { entries }
      )
      .then((r) => r.data),
}


// ── Types ─────────────────────────────────────────────────────────────────

export interface World {
  id: string
  name: string
  description: string
  genre: string | null
  setting: string | null
  rules: string | null
  style_preset: string | null
  narrative_tone: string | null
  pacing_style: string | null
  vocabulary_style: string | null
  style_tags: string[]
  default_time_of_day: string | null
  default_weather: string | null
  default_mood: string | null
  metadata: Record<string, unknown>
  created_at: string
  updated_at: string
}

