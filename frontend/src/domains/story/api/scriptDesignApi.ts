/**
 * 文件说明：前端业务域逻辑与接口封装。
 */

import api from '@/services/api'
import type { World } from '@/services/lorebookService'

export type ScriptDesignStatus = 'draft' | 'active' | 'archived'
export type EventNodeStatus = 'pending' | 'active' | 'completed' | 'skipped'
export type EventNodeType = 'reveal' | 'conflict' | 'transition' | 'climax' | 'recovery' | 'setup' | 'custom'
export type ForeshadowStatus = 'planted' | 'hinted' | 'paid_off' | 'abandoned'
export type ForeshadowCategory = 'object' | 'identity' | 'prophecy' | 'relationship' | 'mystery' | 'rule' | 'custom'
export type ImportanceLevel = 'low' | 'medium' | 'high'

export interface ScriptGenerationPolicy {
  enforce_stage_order: boolean
  enforce_pending_event: boolean
  enforce_foreshadow_tracking: boolean
  preferred_stage_id: string | null
  preferred_event_ids: string[]
  writing_brief: string | null
}

export interface ScriptStage {
  id: string
  title: string
  order: number
  goal: string | null
  tension: string | null
  entry_condition: string | null
  exit_condition: string | null
  expected_turning_point: string | null
  linked_role_ids: string[]
  linked_lorebook_entry_ids: string[]
  notes: string | null
}

export interface ScriptEventNode {
  id: string
  stage_id: string
  title: string
  summary: string | null
  order: number
  status: EventNodeStatus
  event_type: EventNodeType
  trigger_condition: string | null
  objective: string | null
  obstacle: string | null
  expected_outcome: string | null
  failure_outcome: string | null
  scene_hint: string | null
  participant_role_ids: string[]
  participant_lorebook_entry_ids: string[]
  prerequisite_event_ids: string[]
  unlocks_event_ids: string[]
  foreshadow_ids: string[]
  notes: string | null
}

export interface ForeshadowRecord {
  id: string
  title: string
  content: string
  category: ForeshadowCategory
  planted_stage_id: string | null
  planted_event_id: string | null
  expected_payoff_stage_id: string | null
  expected_payoff_event_id: string | null
  payoff_description: string | null
  status: ForeshadowStatus
  importance: ImportanceLevel
  notes: string | null
}

export interface ScriptDesign {
  id: string
  world_id: string
  title: string
  summary: string | null
  logline: string | null
  theme: string | null
  core_conflict: string | null
  ending_direction: string | null
  protagonist_profile: string | null
  tone_style: string | null
  status: ScriptDesignStatus
  stage_outlines: ScriptStage[]
  event_nodes: ScriptEventNode[]
  foreshadows: ForeshadowRecord[]
  default_generation_policy: ScriptGenerationPolicy
  tags: string[]
  version: number
  created_at: string
  updated_at: string
}

export interface StoryBindingSummary {
  story_id: string
  title: string
  world_id: string
  world_name: string
  updated_at: string
}

export interface ScriptDesignBindingsResponse {
  script_design_id: string
  count: number
  items: StoryBindingSummary[]
}

export interface ScriptDesignCreateInput {
  world_id: string
  title: string
  summary?: string | null
  logline?: string | null
  theme?: string | null
  core_conflict?: string | null
  ending_direction?: string | null
  protagonist_profile?: string | null
  tone_style?: string | null
  status?: ScriptDesignStatus
  stage_outlines?: ScriptStage[]
  event_nodes?: ScriptEventNode[]
  foreshadows?: ForeshadowRecord[]
  default_generation_policy?: ScriptGenerationPolicy
  tags?: string[]
}

export interface ScriptDesignUpdateInput {
  title?: string
  summary?: string | null
  logline?: string | null
  theme?: string | null
  core_conflict?: string | null
  ending_direction?: string | null
  protagonist_profile?: string | null
  tone_style?: string | null
  status?: ScriptDesignStatus
  stage_outlines?: ScriptStage[]
  event_nodes?: ScriptEventNode[]
  foreshadows?: ForeshadowRecord[]
  default_generation_policy?: ScriptGenerationPolicy
  tags?: string[]
}

export interface ScriptDesignSidebarWorld extends Pick<World, 'id' | 'name' | 'genre'> {}

// scriptDesignApi 相关状态。
export const scriptDesignApi = {
  list(worldId?: string, status?: ScriptDesignStatus) {
    return api
      .get<ScriptDesign[]>('/script-designs', { params: { world_id: worldId, status } })
      .then((response) => response.data)
  },

  get(scriptDesignId: string) {
    return api
      .get<ScriptDesign>(`/script-designs/${scriptDesignId}`)
      .then((response) => response.data)
  },

  create(payload: ScriptDesignCreateInput) {
    return api
      .post<ScriptDesign>('/script-designs', payload)
      .then((response) => response.data)
  },

  update(scriptDesignId: string, payload: ScriptDesignUpdateInput) {
    return api
      .put<ScriptDesign>(`/script-designs/${scriptDesignId}`, payload)
      .then((response) => response.data)
  },

  remove(scriptDesignId: string) {
    return api
      .delete<{ success: boolean; script_design_id: string }>(`/script-designs/${scriptDesignId}`)
      .then((response) => response.data)
  },

  getStoryBindings(scriptDesignId: string) {
    return api
      .get<ScriptDesignBindingsResponse>(`/script-designs/${scriptDesignId}/story-bindings`)
      .then((response) => response.data)
  },
}