/**
 * 文件说明：前端通用服务与请求能力。
 */

import { z } from 'zod'

// V2ContextItemSchema 相关状态。
export const V2ContextItemSchema = z.object({
  name: z.string(),
  type: z.string(),
  content: z.string(),
  score: z.number(),
})

// MemoryUpdateEventSchema 相关状态。
export const MemoryUpdateEventSchema = z.object({
  event_id: z.string(),
  session_id: z.string(),
  operation_id: z.string().nullable().optional(),
  sequence: z.number().nullable().optional(),
  display_kind: z.string().nullable().optional(),
  memory_layer: z.string(),
  action: z.string(),
  source: z.string(),
  source_turn: z.number().nullable().optional(),
  memory_key: z.string().nullable().optional(),
  title: z.string(),
  reason: z.string().nullable().optional(),
  before: z.record(z.string(), z.unknown()).nullable().optional(),
  after: z.record(z.string(), z.unknown()).nullable().optional(),
  status: z.string().optional(),
  committed_at: z.string(),
})

// SummaryMemorySnapshotSchema 相关状态。
export const SummaryMemorySnapshotSchema = z.object({
  summary_text: z.string(),
  key_facts: z.array(z.string()).optional(),
  last_turn: z.number().optional(),
  session_id: z.string().optional(),
})

// StoryMemoryOperationSchema 相关状态。
export const StoryMemoryOperationSchema = z.object({
  operation_id: z.string().nullable().optional(),
  source: z.string().nullable().optional(),
  status: z.string(),
  committed_at: z.string().nullable().optional(),
  sequence_min: z.number().nullable().optional(),
  sequence_max: z.number().nullable().optional(),
  event_count: z.number().optional(),
  entity_update_count: z.number().optional(),
})

// EntityStateSnapshotSchema 相关状态。
export const EntityCompanionRefSchema = z.object({
  id: z.string(),
  display_name: z.string(),
})

export const EntityStateSnapshotSchema = z.object({
  story_id: z.string(),
  session_id: z.string(),
  entity_id: z.string(),
  entity_type: z.literal('character'),
  display_name: z.string(),
  current_location: z.string().nullable().optional(),
  inventory: z.array(z.string()),
  status_tags: z.array(z.string()),
  companions: z.array(z.union([z.string(), EntityCompanionRefSchema])),
  short_goal: z.string().nullable().optional(),
  state_summary: z.string().nullable().optional(),
  evidence: z.array(z.string()),
  last_source_turn: z.number().nullable().optional(),
  updated_at: z.string(),
  version: z.number(),
  metadata: z.record(z.string(), z.unknown()),
})

// EntityStateCollectionSchema 相关状态。
export const EntityStateCollectionSchema = z.object({
  story_id: z.string().nullable().optional(),
  session_id: z.string(),
  entity_type: z.literal('character').nullable().optional(),
  items: z.array(EntityStateSnapshotSchema),
  total: z.number(),
})

// EntityStateUpdateSchema 相关状态。
export const EntityStateUpdateSchema = z.object({
  event_id: z.string(),
  story_id: z.string(),
  session_id: z.string(),
  entity_id: z.string(),
  entity_type: z.literal('character'),
  entity_name: z.string().nullable().optional(),
  field_name: z.string(),
  op: z.string(),
  value: z.unknown().nullable().optional(),
  before: z.unknown().nullable().optional(),
  after: z.unknown().nullable().optional(),
  evidence_text: z.string().nullable().optional(),
  source_turn: z.number().nullable().optional(),
  source: z.string(),
  operation_id: z.string().nullable().optional(),
  sequence: z.number().nullable().optional(),
  confidence: z.number().nullable().optional(),
  status: z.string(),
  committed_at: z.string(),
  metadata: z.record(z.string(), z.unknown()).optional(),
})

// StoryMemoryPayloadSchema 相关状态。
export const StoryMemoryPayloadSchema = z.object({
  session_id: z.string(),
  story_id: z.string().nullable().optional(),
  world_id: z.string().nullable().optional(),
  operation: StoryMemoryOperationSchema.nullable().optional(),
  semantic: z.object({
    summary_memory_snapshot: SummaryMemorySnapshotSchema.nullable().optional(),
  }).nullable().optional(),
  runtime: z.object({
    runtime_state_snapshot: z.record(z.string(), z.unknown()).nullable().optional(),
  }).nullable().optional(),
  entity: z.object({
    entity_state_snapshot: EntityStateCollectionSchema.nullable().optional(),
    entity_state_updates: z.array(EntityStateUpdateSchema).optional(),
    world_update: z.record(z.string(), z.unknown()).nullable().optional(),
  }).nullable().optional(),
  timeline: z.object({
    memory_updates: z.array(MemoryUpdateEventSchema).optional(),
  }).nullable().optional(),
})

// V2GenerateResponseSchema 相关状态。
export const V2GenerateResponseSchema = z.object({
  session_id: z.string(),
  thread_id: z.string(),
  output_text: z.string(),
  contexts: z.array(V2ContextItemSchema),
  activation_logs: z.array(z.record(z.string(), z.unknown())).optional(),
  memory_updates: z.array(MemoryUpdateEventSchema).optional(),
  story_state_snapshot: z.record(z.string(), z.unknown()).nullable().optional(),
  story_memory: StoryMemoryPayloadSchema.nullable().optional(),
  summary_memory_snapshot: SummaryMemorySnapshotSchema.nullable().optional(),
  runtime_state_snapshot: z.record(z.string(), z.unknown()).nullable().optional(),
  entity_state_snapshot: EntityStateCollectionSchema.nullable().optional(),
  entity_state_updates: z.array(EntityStateUpdateSchema).nullable().optional(),
  world_update: z.record(z.string(), z.unknown()).nullable().optional(),
  creation_mode: z.string().nullable().optional(),
  consistency_check: z.record(z.string(), z.unknown()).nullable().optional(),
  model: z.string(),
  generation_time: z.number(),
  choices: z.array(z.string()).optional(),
  tokens_used: z
    .object({
      input_tokens: z.number(),
      output_tokens: z.number(),
      total_tokens: z.number(),
    })
    .nullable()
    .optional(),
  token_source: z.string().nullable().optional(),
})
