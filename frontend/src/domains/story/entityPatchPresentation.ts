/**
 * 文件说明：前端业务域逻辑与接口封装。
 */

import type { EntityStateUpdate } from '@/domains/story/api/storyGenerationApi'
import type { EntityStateCollection, MemoryUpdateEvent } from '@/domains/story/api/storyGenerationApi'
import { getEntityCompanionDisplayName, getEntityCompanionId } from '@/domains/story/entityCompanion'
import type { StoryEntityUpdateRecord, StoryWorldUpdateRecord } from '@/stores/storySession'

type EntityLikeUpdate = EntityStateUpdate | StoryEntityUpdateRecord

const ENTITY_FIELD_LABELS: Record<string, string> = {
  display_name: '显示名称',
  current_location: '位置',
  inventory: '携带物',
  status_tags: '状态标签',
  companions: '同行者',
  state_summary: '状态摘要',
  short_goal: '当前目标',
  evidence: '证据',
  last_source_turn: '最后来源轮次',
  updated_at: '更新时间',
  entity_id: '实体 ID',
}

/** 统一返回实体字段的中文展示名。 */
export function getEntityFieldLabel(fieldName?: string | null): string {
  const normalizedFieldName = typeof fieldName === 'string' ? fieldName.trim() : ''
  if (!normalizedFieldName) return '实体状态'
  return ENTITY_FIELD_LABELS[normalizedFieldName] ?? normalizedFieldName
}

/** 处理 isApiEntityUpdate 相关逻辑。 */
function isApiEntityUpdate(update: EntityLikeUpdate): update is EntityStateUpdate {
  return 'entity_name' in update || 'field_name' in update
}

function extractDisplayName(value: unknown): string | null {
  if (!value || typeof value !== 'object') return null
  const displayName = (value as Record<string, unknown>).display_name
  return typeof displayName === 'string' && displayName.trim() ? displayName.trim() : null
}

function normalizeEntityId(value?: string | null): string | null {
  const normalizedValue = typeof value === 'string' ? value.trim() : ''
  return normalizedValue || null
}

function extractEntityIdFromMemoryKey(memoryKey?: string | null): string | null {
  const normalizedMemoryKey = normalizeEntityId(memoryKey)
  if (!normalizedMemoryKey) return null
  const [entityId] = normalizedMemoryKey.split(':')
  return normalizeEntityId(entityId)
}

/** 处理 resolveEntityName 相关逻辑。 */
function resolveEntityName(update: EntityLikeUpdate): string {
  if (isApiEntityUpdate(update)) {
    return update.entity_name ?? update.entity_id
  }
  return update.entityName
    ?? extractDisplayName(update.after)
    ?? extractDisplayName(update.before)
    ?? update.entityId
    ?? '未知实体'
}

/** 处理 resolveFieldName 相关逻辑。 */
function resolveFieldName(update: EntityLikeUpdate): string {
  if (isApiEntityUpdate(update)) {
    return update.field_name
  }
  return update.fieldName
}

/** 统一返回 patch 对应的原始字段名。 */
export function getEntityPatchFieldName(update: EntityLikeUpdate): string {
  return resolveFieldName(update) ?? ''
}

/** 处理 compactText 相关逻辑。 */
function compactText(value: string, maxLength: number): string {
  return value.length > maxLength ? `${value.slice(0, maxLength - 1)}…` : value
}

function isStructuredValue(value: unknown): boolean {
  if (Array.isArray(value)) {
    return value.some((item) => item != null && typeof item === 'object')
  }
  return value != null && typeof value === 'object'
}

/** 处理 formatEntityPatchValue 相关逻辑。 */
export function formatEntityPatchValue(value: unknown): string {
  if (value == null) return '空'
  if (Array.isArray(value)) {
    return value.map((item) => formatEntityPatchValue(item)).join('、') || '空'
  }
  if (typeof value === 'object') {
    const companionDisplayName = getEntityCompanionDisplayName(value)
    if (companionDisplayName) return companionDisplayName
    const companionId = getEntityCompanionId(value)
    if (companionId) return companionId
    try {
      return JSON.stringify(value, null, 2)
    } catch {
      return String(value)
    }
  }
  return String(value)
}

/** 处理 getEntityPatchEntityLabel 相关逻辑。 */
export function getEntityPatchEntityLabel(update: EntityLikeUpdate): string {
  return resolveEntityName(update)
}

export function buildEntityNameMap(options: {
  snapshot?: EntityStateCollection | null
  updates?: EntityLikeUpdate[]
  events?: Array<Pick<MemoryUpdateEvent, 'memory_layer' | 'memory_key' | 'before' | 'after'>>
  lorebookEntries?: Array<{
    id?: string | null
    name?: string | null
    type?: string | null
  }>
}): Map<string, string> {
  const nameMap = new Map<string, string>()

  for (const item of options.snapshot?.items ?? []) {
    const entityId = normalizeEntityId(item.entity_id)
    const displayName = item.display_name?.trim()
    if (entityId && displayName) {
      nameMap.set(entityId, displayName)
    }
  }

  for (const update of options.updates ?? []) {
    const entityId = normalizeEntityId(isApiEntityUpdate(update) ? update.entity_id : update.entityId)
    const displayName = resolveEntityName(update)?.trim()
    if (entityId && displayName) {
      nameMap.set(entityId, displayName)
    }
  }

  for (const event of options.events ?? []) {
    if (event.memory_layer !== 'entity_state') continue
    const entityId = extractEntityIdFromMemoryKey(event.memory_key)
    const displayName = extractDisplayName(event.after) ?? extractDisplayName(event.before)
    if (entityId && displayName) {
      nameMap.set(entityId, displayName)
    }
  }

  for (const entry of options.lorebookEntries ?? []) {
    const entryId = normalizeEntityId(entry.id)
    const entryName = typeof entry.name === 'string' ? entry.name.trim() : ''
    if (entry.type !== 'character') continue
    if (entryId && entryName && !nameMap.has(entryId)) {
      nameMap.set(entryId, entryName)
    }
  }

  return nameMap
}

/** 处理 getEntityPatchFieldLabel 相关逻辑。 */
export function getEntityPatchFieldLabel(update: EntityLikeUpdate): string {
  const fieldName = resolveFieldName(update)
  return getEntityFieldLabel(fieldName)
}

/** 处理 getEntityPatchOperationLabel 相关逻辑。 */
export function getEntityPatchOperationLabel(op: string): string {
  switch (op) {
    case 'set':
    case 'replace':
      return '更新'
    case 'add':
    case 'append':
      return '新增'
    case 'remove':
      return '移除'
    case 'rebuild':
      return '重建'
    default:
      return op
  }
}

/** 处理 getEntityPatchHeadline 相关逻辑。 */
export function getEntityPatchHeadline(update: EntityLikeUpdate): string {
  return `${resolveEntityName(update)} · ${resolveFieldName(update)} · ${update.op}`
}

/** 处理 getEntityPatchDetail 相关逻辑。 */
export function getEntityPatchDetail(update: EntityLikeUpdate): string {
  const before = 'before' in update ? update.before : null
  const after = 'after' in update ? update.after : null
  const value = 'value' in update ? update.value : null
  if (after != null || before != null) {
    return `${formatEntityPatchValue(before)} → ${formatEntityPatchValue(after)}`
  }
  return formatEntityPatchValue(value)
}

/** 处理 getEntityPatchChangeSummary 相关逻辑。 */
export function getEntityPatchChangeSummary(update: EntityLikeUpdate, maxLength = 80): string {
  const fieldLabel = getEntityPatchFieldLabel(update)
  const before = 'before' in update ? update.before : null
  const after = 'after' in update ? update.after : null
  const value = 'value' in update ? update.value : null

  if (update.op === 'remove') {
    const removedValue = before ?? value ?? after
    if (isStructuredValue(removedValue)) {
      return `${fieldLabel}：已移除`
    }
    return `${fieldLabel}：移除 ${compactText(formatEntityPatchValue(removedValue), maxLength)}`
  }

  if (before != null || after != null) {
    if (isStructuredValue(before) || isStructuredValue(after)) {
      return `${fieldLabel}：已更新`
    }
    return `${fieldLabel}：${compactText(formatEntityPatchValue(before), maxLength)} -> ${compactText(formatEntityPatchValue(after), maxLength)}`
  }

  if (value != null) {
    if (isStructuredValue(value)) {
      return `${fieldLabel}：${getEntityPatchOperationLabel(update.op)}`
    }
    return `${fieldLabel}：${compactText(formatEntityPatchValue(value), maxLength)}`
  }

  return `${fieldLabel}：${getEntityPatchOperationLabel(update.op)}`
}

/** 处理 getEntityPatchEventId 相关逻辑。 */
export function getEntityPatchEventId(update: EntityLikeUpdate): string {
  return 'event_id' in update ? update.event_id : update.eventId
}

/** 处理 getEntityPatchSourceTurn 相关逻辑。 */
export function getEntityPatchSourceTurn(update: EntityLikeUpdate): number | null {
  return isApiEntityUpdate(update) ? (update.source_turn ?? null) : (update.sourceTurn ?? null)
}

/** 处理 getEntityPatchCommittedAt 相关逻辑。 */
export function getEntityPatchCommittedAt(update: EntityLikeUpdate): string {
  return 'committed_at' in update ? update.committed_at : update.committedAt
}

/** 处理 getEntityPatchEvidenceText 相关逻辑。 */
export function getEntityPatchEvidenceText(update: EntityLikeUpdate): string | null {
  return isApiEntityUpdate(update) ? (update.evidence_text ?? null) : (update.evidenceText ?? null)
}

/** 处理 extractWorldUpdateHighlights 相关逻辑。 */
export function extractWorldUpdateHighlights(worldUpdate: Record<string, unknown> | StoryWorldUpdateRecord | null | undefined): string[] {
  const payload: Record<string, unknown> | null = worldUpdate
    ? ('payload' in worldUpdate
        ? (worldUpdate.payload as Record<string, unknown>)
        : worldUpdate)
    : null
  if (!payload) return []

  const entityPatch = payload.entity_patch
  if (entityPatch && typeof entityPatch === 'object') {
    const patchPayload = entityPatch as Record<string, unknown>
    const highlights: string[] = []
    const patchCount = patchPayload.patch_count
    if (typeof patchCount === 'number') {
      highlights.push(`本轮应用 ${patchCount} 条实体 patch`)
    }
    const fallbackUsed = patchPayload.fallback_used
    if (typeof fallbackUsed === 'boolean') {
      highlights.push(fallbackUsed ? '本轮使用 fallback rebuild' : '本轮直接采用 patch 投影')
    }
    const warnings = patchPayload.warnings
    if (Array.isArray(warnings) && warnings.length) {
      highlights.push(`告警：${warnings.slice(0, 2).map((item) => String(item)).join('；')}`)
    }
    return highlights
  }

  return Object.entries(payload)
    .slice(0, 3)
    .map(([key, value]) => `${key}: ${formatEntityPatchValue(value)}`)
}
