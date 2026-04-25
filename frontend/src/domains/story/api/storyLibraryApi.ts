/**
 * 文件说明：前端业务域逻辑与接口封装。
 */

import api from '@/services/api'
import type { StoredStory } from '@/components/story/types'
import type { EntityStateCollection, MemoryUpdateEvent } from '@/domains/story/api/storyGenerationApi'

export interface CreateStoryPayload {
  world_id: string
  title: string
}

export interface UpdateStoryPayload {
  title?: string
  metadata?: Record<string, unknown>
}

export interface UpdateStoryProgressPayload {
  script_design_id?: string | null
  active_stage_id?: string | null
  active_event_id?: string | null
  follow_script_design?: boolean
  creation_mode?: 'improv' | 'scripted' | null
  runtime_state_id?: string | null
}

export interface StoryRuntimeState {
  id: string
  story_id: string
  session_id: string
  world_id?: string | null
  script_design_id: string
  creation_mode: 'improv' | 'scripted'
  current_stage_id?: string | null
  current_event_id?: string | null
  completed_event_ids: string[]
  skipped_event_ids: string[]
  active_foreshadow_ids: string[]
  paid_off_foreshadow_ids: string[]
  abandoned_foreshadow_ids: string[]
  current_location_entry_id?: string | null
  current_time_label?: string | null
  active_character_entry_ids: string[]
  runtime_notes?: string | null
  last_contract_snapshot?: Record<string, unknown> | null
  last_check_result?: Record<string, unknown> | null
  created_at: string
  updated_at: string
}

export interface UpdateStoryRuntimePayload {
  script_design_id?: string
  creation_mode?: 'improv' | 'scripted'
  current_stage_id?: string | null
  current_event_id?: string | null
  completed_event_ids?: string[]
  skipped_event_ids?: string[]
  active_foreshadow_ids?: string[]
  paid_off_foreshadow_ids?: string[]
  abandoned_foreshadow_ids?: string[]
  current_location_entry_id?: string | null
  current_time_label?: string | null
  active_character_entry_ids?: string[]
  runtime_notes?: string | null
  last_contract_snapshot?: Record<string, unknown> | null
  last_check_result?: Record<string, unknown> | null
}

export interface SaveStorySegmentPayload {
  prompt: string
  creation_mode?: 'improv' | 'scripted'
  content: string
  retrieved_context: string[]
  runtime_state_snapshot?: Record<string, unknown> | null
}

export interface DeleteLastStorySegmentResponse {
  story: StoredStory
  runtime_state?: StoryRuntimeState | null
}

export interface StorySegmentContentUpdatePayload {
  segment_id: string
  content: string
}

export interface CommitStoryAdjustmentsPayload {
  session_id?: string
  updates: StorySegmentContentUpdatePayload[]
}

export interface CommitStoryAdjustmentsResponse {
  story: StoredStory
  session_id: string
  rebuild_summary_reset: boolean
  rebuild_history_reindexed: boolean
  rebuild_entity_state_rebuilt: boolean
  memory_updates: MemoryUpdateEvent[]
  warnings: string[]
}

// storyLibraryApi 相关状态。
export const storyLibraryApi = {
  listByWorld(worldId: string) {
    return api
      .get<StoredStory[]>('/stories', { params: { world_id: worldId } })
      .then((response) => response.data)
  },

  get(storyId: string) {
    return api
      .get<StoredStory>(`/stories/${storyId}`)
      .then((response) => response.data)
  },

  create(payload: CreateStoryPayload) {
    return api
      .post<StoredStory>('/stories', payload)
      .then((response) => response.data)
  },

  update(storyId: string, payload: UpdateStoryPayload) {
    return api
      .put<StoredStory>(`/stories/${storyId}`, payload)
      .then((response) => response.data)
  },

  updateProgress(storyId: string, payload: UpdateStoryProgressPayload) {
    return api
      .put<StoredStory>(`/stories/${storyId}/progress`, payload)
      .then((response) => response.data)
  },

  getRuntime(storyId: string) {
    return api
      .get<StoryRuntimeState>(`/stories/${storyId}/runtime`)
      .then((response) => response.data)
  },

  getEntityState(storyId: string) {
    return api
      .get<EntityStateCollection>(`/stories/${storyId}/entity-state`)
      .then((response) => response.data)
  },

  updateRuntime(storyId: string, payload: UpdateStoryRuntimePayload) {
    return api
      .put<StoryRuntimeState>(`/stories/${storyId}/runtime`, payload)
      .then((response) => response.data)
  },

  remove(storyId: string) {
    return api.delete(`/stories/${storyId}`).then(() => undefined)
  },

  appendSegment(storyId: string, payload: SaveStorySegmentPayload) {
    return api.post(`/stories/${storyId}/segments`, payload).then(() => undefined)
  },

  deleteLastSegment(storyId: string) {
    return api
      .delete<DeleteLastStorySegmentResponse>(`/stories/${storyId}/segments/last`)
      .then((response) => response.data)
  },

  commitAdjustments(storyId: string, payload: CommitStoryAdjustmentsPayload) {
    return api
      .post<CommitStoryAdjustmentsResponse>(`/stories/${storyId}/adjustments/commit`, payload)
      .then((response) => response.data)
  },
}
