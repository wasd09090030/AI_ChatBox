/**
 * 文件说明：前端业务域逻辑与接口封装。
 */

import api from '@/services/api'
import { ZodError } from 'zod'
import { createAppError, normalizeApiError } from '@/services/errors'
import { V2GenerateResponseSchema } from '@/services/schemas'
import { API_PREFIX } from '@/utils/constants'

const MAX_CHOICES = 3

/** 处理 getStoryHeaders 相关逻辑。 */
function getStoryHeaders(contentType = true): Record<string, string> {
  const headers: Record<string, string> = {}
  if (contentType) {
    headers['Content-Type'] = 'application/json'
  }
  return headers
}

/** 处理 buildStorySessionId 相关逻辑。 */
export function buildStorySessionId(storyId: string): string {
  return `story-${storyId}-v2`
}

export interface V2ContextItem {
  name: string
  type: string
  content: string
  score: number
}

export interface V2GenerateRequest {
  session_id: string
  story_id?: string
  thread_id?: string
  user_input: string
  world_id?: string
  creation_mode?: 'improv' | 'scripted'
  progress_intent?: 'hold' | 'advance' | 'complete'
  runtime_state_id?: string
  allow_state_transition?: boolean
  character_card_id?: string
  persona_id?: string
  script_design_id?: string
  active_stage_id?: string
  active_event_id?: string
  follow_script_design?: boolean
  principal_character_id?: string
  dialogue_mode?: 'auto' | 'focused' | 'required'
  dialogue_target?: string
  dialogue_intent?: string
  dialogue_style_hint?: string
  force_dialogue_round?: boolean
  story_state_mode?: 'off' | 'light' | 'strict'
  model?: string
  provider?: string
  base_url?: string
  temperature?: number
  max_tokens?: number
  use_rag?: boolean
  top_k?: number
  style?: string
  language?: string
  authors_note?: string
  mode?: 'narrative' | 'choices' | 'instruction'
  instruction?: string
  selected_context_entry_ids?: string[]
  focus_instruction?: string
  focus_label?: string
  enhance_input?: boolean
}

export interface V2GenerateResponse {
  session_id: string
  thread_id: string
  output_text: string
  contexts: V2ContextItem[]
  activation_logs?: Array<Record<string, unknown>>
  memory_updates?: MemoryUpdateEvent[]
  story_state_snapshot?: Record<string, unknown> | null
  story_memory?: StoryMemoryPayload | null
  summary_memory_snapshot?: SummaryMemorySnapshot | null
  runtime_state_snapshot?: Record<string, unknown> | null
  entity_state_snapshot?: EntityStateCollection | null
  entity_state_updates?: EntityStateUpdate[] | null
  world_update?: Record<string, unknown> | null
  creation_mode?: string | null
  consistency_check?: Record<string, unknown> | null
  model: string
  generation_time: number
  choices?: string[]
  tokens_used?: { input_tokens: number; output_tokens: number; total_tokens: number } | null
  token_source?: 'provider_usage' | 'estimated' | string | null
}

export interface V2InputEnhancementPreviewRequest {
  session_id: string
  story_id?: string
  user_input: string
  world_id?: string
  creation_mode?: 'improv' | 'scripted'
  progress_intent?: 'hold' | 'advance' | 'complete'
  runtime_state_id?: string
  allow_state_transition?: boolean
  character_card_id?: string
  persona_id?: string
  script_design_id?: string
  active_stage_id?: string
  active_event_id?: string
  follow_script_design?: boolean
  principal_character_id?: string
  dialogue_mode?: 'auto' | 'focused' | 'required'
  dialogue_target?: string
  dialogue_intent?: string
  dialogue_style_hint?: string
  force_dialogue_round?: boolean
  model?: string
  provider?: string
  base_url?: string
  temperature?: number
  selected_context_entry_ids?: string[]
  focus_instruction?: string
  focus_label?: string
}

export interface V2InputEnhancementPreviewResponse {
  original_text: string
  enhanced_text: string
  applied: boolean
  reason?: string | null
}

export interface SummaryMemorySnapshot {
  summary_text: string
  key_facts?: string[]
  last_turn?: number
  session_id?: string
}

export interface EntityCompanionRef {
  id: string
  display_name: string
}

export type EntityCompanion = string | EntityCompanionRef

export interface EntityStateSnapshot {
  story_id: string
  session_id: string
  entity_id: string
  entity_type: 'character'
  display_name: string
  current_location?: string | null
  inventory: string[]
  status_tags: string[]
  companions: EntityCompanion[]
  short_goal?: string | null
  state_summary?: string | null
  evidence: string[]
  last_source_turn?: number | null
  updated_at: string
  version: number
  metadata: Record<string, unknown>
}

export interface EntityStateCollection {
  story_id?: string | null
  session_id: string
  entity_type?: 'character' | null
  items: EntityStateSnapshot[]
  total: number
}

export interface EntityStateUpdate {
  event_id: string
  story_id: string
  session_id: string
  entity_id: string
  entity_type: 'character'
  entity_name?: string | null
  field_name: string
  op: string
  value?: unknown
  before?: unknown
  after?: unknown
  evidence_text?: string | null
  source_turn?: number | null
  source: string
  operation_id?: string | null
  sequence?: number | null
  confidence?: number | null
  status: string
  committed_at: string
  metadata?: Record<string, unknown>
}

export interface StoryMemoryOperation {
  operation_id?: string | null
  source?: string | null
  status: string
  committed_at?: string | null
  sequence_min?: number | null
  sequence_max?: number | null
  event_count?: number
  entity_update_count?: number
}

export interface StoryMemoryPayload {
  session_id: string
  story_id?: string | null
  world_id?: string | null
  operation?: StoryMemoryOperation | null
  semantic?: {
    summary_memory_snapshot?: SummaryMemorySnapshot | null
  } | null
  runtime?: {
    runtime_state_snapshot?: Record<string, unknown> | null
  } | null
  entity?: {
    entity_state_snapshot?: EntityStateCollection | null
    entity_state_updates?: EntityStateUpdate[]
    world_update?: Record<string, unknown> | null
  } | null
  timeline?: {
    memory_updates?: MemoryUpdateEvent[]
  } | null
}

export interface StoryActivationLog {
  source?: string
  selection_mode?: 'explicit' | 'rag' | string
  event?: string
  entry_name?: string
  entry_type?: string
  score?: number
  rrf_score?: number
}

export interface MemoryUpdateEvent {
  event_id: string
  session_id: string
  operation_id?: string | null
  sequence?: number | null
  display_kind?: string | null
  memory_layer: 'episodic' | 'semantic' | 'profile' | 'procedural' | 'system' | string
  action: 'created' | 'merged' | 'updated' | 'reset' | 'reindexed' | 'superseded' | 'marked_stale' | 'rebuilt' | string
  source: string
  source_turn?: number | null
  memory_key?: string | null
  title: string
  reason?: string | null
  before?: Record<string, unknown> | null
  after?: Record<string, unknown> | null
  status?: 'committed' | 'failed' | 'stale' | string
  committed_at: string
}

export interface StreamEvent {
  type: 'chunk' | 'done' | 'error'
  content?: string
  session_id?: string
  generated_text?: string
  output_text?: string
  choices?: string[]
  activation_logs?: StoryActivationLog[]
  memory_updates?: MemoryUpdateEvent[]
  story_memory?: StoryMemoryPayload | null
  summary_memory_snapshot?: SummaryMemorySnapshot | null
  runtime_state_snapshot?: Record<string, unknown> | null
  entity_state_snapshot?: EntityStateCollection | null
  entity_state_updates?: EntityStateUpdate[] | null
  world_update?: Record<string, unknown> | null
  creation_mode?: string | null
  consistency_check?: Record<string, unknown> | null
  tokens_used?: { input_tokens: number; output_tokens: number; total_tokens: number } | null
  token_source?: 'provider_usage' | 'estimated' | string | null
  generation_time?: number
  message?: string
}

export interface SessionInfo {
  session_id: string
  message_count: number
  created_at?: string | null
}

export interface DeleteLastMessageResponse {
  deleted: boolean
  session_id: string
  detail?: string | null
  memory_updates?: MemoryUpdateEvent[]
}

export interface RegenerateRequest {
  story_id?: string
  persona_id?: string
  model?: string
  provider?: string
  base_url?: string
  temperature?: number
  max_tokens?: number
  authors_note?: string
  mode?: 'narrative' | 'choices' | 'instruction'
  instruction?: string
  selected_context_entry_ids?: string[]
  script_design_id?: string
  active_stage_id?: string
  active_event_id?: string
  follow_script_design?: boolean
  creation_mode?: 'improv' | 'scripted'
  progress_intent?: 'hold' | 'advance' | 'complete'
  runtime_state_id?: string
  allow_state_transition?: boolean
  principal_character_id?: string
  dialogue_mode?: 'auto' | 'focused' | 'required'
  dialogue_target?: string
  dialogue_intent?: string
  dialogue_style_hint?: string
  force_dialogue_round?: boolean
  focus_instruction?: string
  focus_label?: string
}

export async function* streamStoryV2(
  payload: V2GenerateRequest,
  signal?: AbortSignal,
): AsyncGenerator<StreamEvent> {
  const url = `${API_PREFIX}/story/generate/stream`
  const response = await fetch(url, {
    method: 'POST',
    credentials: 'include',
    headers: getStoryHeaders(true),
    body: JSON.stringify(payload),
    signal,
  })
  if (!response.ok) {
    const text = await response.text().catch(() => '')
    throw new Error(`流式生成请求失败 (${response.status}): ${text}`)
  }
  const reader = response.body!.getReader()
  const decoder = new TextDecoder()
  let buffer = ''
  let shouldCancelReader = true

  const parseStreamLine = (line: string): StreamEvent | null => {
    if (!line.startsWith('data: ')) return null
    try {
      const raw = JSON.parse(line.slice(6)) as Record<string, unknown>
      if (raw['done'] === false) {
        return { type: 'chunk', content: raw['chunk'] as string } satisfies StreamEvent
      }
      if (raw['done'] === true) {
        const rawGenerated = raw['generated_text'] ?? raw['output_text']
        const generated = typeof rawGenerated === 'string' ? rawGenerated : undefined
        const choices = Array.isArray(raw['choices'])
          ? raw['choices'].map((item) => String(item).trim()).filter(Boolean).slice(0, MAX_CHOICES)
          : undefined
        return {
          type: 'done',
          session_id: raw['session_id'] as string | undefined,
          generated_text: generated,
          output_text: generated,
          choices,
          generation_time: raw['generation_time'] as number | undefined,
          activation_logs: raw['activation_logs'] as StoryActivationLog[] | undefined,
          memory_updates: raw['memory_updates'] as MemoryUpdateEvent[] | undefined,
          story_memory: (raw['story_memory'] ?? null) as StoryMemoryPayload | null,
          summary_memory_snapshot: (raw['summary_memory_snapshot'] ?? null) as SummaryMemorySnapshot | null,
          runtime_state_snapshot: (raw['runtime_state_snapshot'] ?? null) as Record<string, unknown> | null,
          entity_state_snapshot: (raw['entity_state_snapshot'] ?? null) as EntityStateCollection | null,
          entity_state_updates: (raw['entity_state_updates'] ?? null) as EntityStateUpdate[] | null,
          world_update: (raw['world_update'] ?? null) as Record<string, unknown> | null,
          creation_mode: (raw['creation_mode'] ?? null) as string | null,
          consistency_check: (raw['consistency_check'] ?? null) as Record<string, unknown> | null,
          tokens_used: (raw['tokens_used'] ?? null) as { input_tokens: number; output_tokens: number; total_tokens: number } | null,
          token_source: (raw['token_source'] ?? null) as 'provider_usage' | 'estimated' | string | null,
        } satisfies StreamEvent
      }
      if (raw['type'] === 'error') {
        return { type: 'error', message: raw['message'] as string | undefined } satisfies StreamEvent
      }
    } catch {
      return null
    }
    return null
  }

  try {
    while (true) {
      const { done, value } = await reader.read()
      if (done) {
        const finalLine = buffer.trim()
        if (finalLine) {
          const event = parseStreamLine(finalLine)
          if (event) {
            yield event
            if (event.type === 'done' || event.type === 'error') {
              shouldCancelReader = false
              return
            }
          }
        }
        break
      }
      buffer += decoder.decode(value, { stream: true })
      const lines = buffer.split('\n')
      buffer = lines.pop() ?? ''
      for (const line of lines) {
        const event = parseStreamLine(line)
        if (!event) continue
        yield event
        if (event.type === 'done' || event.type === 'error') {
          shouldCancelReader = false
          return
        }
      }
    }
  } finally {
    if (shouldCancelReader) {
      try {
        await reader.cancel()
      } catch {
        // Ignore cancel failures when the stream is already closed.
      }
    }
    reader.releaseLock()
  }
}

/** 处理 createSessionV2 相关逻辑。 */
export async function createSessionV2(
  sessionId: string,
  worldId?: string,
): Promise<SessionInfo> {
  const res = await api.post<SessionInfo>(
    '/story/session',
    {
      session_id: sessionId,
      world_id: worldId,
    },
    {
      headers: getStoryHeaders(false),
    },
  )
  return res.data
}

/** 处理 getSessionV2 相关逻辑。 */
export async function getSessionV2(sessionId: string): Promise<SessionInfo> {
  const res = await api.get<SessionInfo>(`/story/session/${encodeURIComponent(sessionId)}`, {
    headers: getStoryHeaders(false),
  })
  return res.data
}

/** 处理 rollbackLastMessageApi 相关逻辑。 */
export async function rollbackLastMessageApi(sessionId: string): Promise<DeleteLastMessageResponse> {
  const response = await api.delete<DeleteLastMessageResponse>(`/story/session/${encodeURIComponent(sessionId)}/messages/last`, {
    headers: getStoryHeaders(false),
  })
  return response.data
}

/** 处理 regenerateStoryApi 相关逻辑。 */
export async function regenerateStoryApi(
  sessionId: string,
  payload: RegenerateRequest = {},
): Promise<V2GenerateResponse> {
  try {
    const res = await api.post<V2GenerateResponse>(
      `/story/session/${encodeURIComponent(sessionId)}/regenerate`,
      payload,
      {
        headers: getStoryHeaders(false),
      },
    )
    return V2GenerateResponseSchema.parse(res.data)
  } catch (error) {
    if (error instanceof ZodError) {
      throw createAppError('重生成响应格式不符合预期', 'SCHEMA_VALIDATION_ERROR', undefined, error.issues)
    }
    throw normalizeApiError(error)
  }
}

/** 处理 generateStoryV2 相关逻辑。 */
export async function generateStoryV2(
  payload: V2GenerateRequest,
  options?: { abortSignal?: AbortSignal },
): Promise<V2GenerateResponse> {
  try {
    const response = await api.post('/story/generate', payload, {
      signal: options?.abortSignal,
      headers: getStoryHeaders(false),
    })
    return V2GenerateResponseSchema.parse(response.data)
  } catch (error) {
    if (error instanceof ZodError) {
      throw createAppError('服务端响应格式不符合预期', 'SCHEMA_VALIDATION_ERROR', undefined, error.issues)
    }
    throw normalizeApiError(error)
  }
}

/** 处理 previewEnhancedStoryInput 相关逻辑。 */
export async function previewEnhancedStoryInput(
  payload: V2InputEnhancementPreviewRequest,
  options?: { abortSignal?: AbortSignal },
): Promise<V2InputEnhancementPreviewResponse> {
  const response = await api.post<V2InputEnhancementPreviewResponse>(
    '/story/input-enhancement/preview',
    payload,
    {
      signal: options?.abortSignal,
      headers: getStoryHeaders(false),
    },
  )
  return response.data
}
