/**
 * 文件说明：前端业务域逻辑与接口封装。
 */

import type { EntityStateUpdate } from '@/domains/story/api/storyGenerationApi'
import type { StoryEntityUpdateRecord, StoryWorldUpdateRecord } from '@/stores/storySession'

type EntityLikeUpdate = EntityStateUpdate | StoryEntityUpdateRecord

const ENTITY_FIELD_LABELS: Record<string, string> = {
  current_location: '位置',
  inventory: '携带物',
  status_tags: '状态标签',
  companions: '同行角色',
  state_summary: '状态摘要',
  short_goal: '当前目标',
}

/** 功能：函数 isApiEntityUpdate，负责 isApiEntityUpdate 相关处理。 */
function isApiEntityUpdate(update: EntityLikeUpdate): update is EntityStateUpdate {
  return 'entity_name' in update || 'field_name' in update
}

/** 功能：函数 resolveEntityName，负责 resolveEntityName 相关处理。 */
function resolveEntityName(update: EntityLikeUpdate): string {
  if (isApiEntityUpdate(update)) {
    return update.entity_name ?? update.entity_id
  }
  return update.entityName ?? update.entityId
}

/** 功能：函数 resolveFieldName，负责 resolveFieldName 相关处理。 */
function resolveFieldName(update: EntityLikeUpdate): string {
  if (isApiEntityUpdate(update)) {
    return update.field_name
  }
  return update.fieldName
}

/** 功能：函数 compactText，负责 compactText 相关处理。 */
function compactText(value: string, maxLength: number): string {
  return value.length > maxLength ? `${value.slice(0, maxLength - 1)}…` : value
}

/** 功能：函数 formatEntityPatchValue，负责 formatEntityPatchValue 相关处理。 */
export function formatEntityPatchValue(value: unknown): string {
  if (value == null) return '空'
  if (Array.isArray(value)) {
    return value.map((item) => formatEntityPatchValue(item)).join('、') || '空'
  }
  if (typeof value === 'object') {
    try {
      return JSON.stringify(value, null, 2)
    } catch {
      return String(value)
    }
  }
  return String(value)
}

/** 功能：函数 getEntityPatchEntityLabel，负责 getEntityPatchEntityLabel 相关处理。 */
export function getEntityPatchEntityLabel(update: EntityLikeUpdate): string {
  return resolveEntityName(update)
}

/** 功能：函数 getEntityPatchFieldLabel，负责 getEntityPatchFieldLabel 相关处理。 */
export function getEntityPatchFieldLabel(update: EntityLikeUpdate): string {
  const fieldName = resolveFieldName(update)
  return ENTITY_FIELD_LABELS[fieldName] ?? fieldName
}

/** 功能：函数 getEntityPatchOperationLabel，负责 getEntityPatchOperationLabel 相关处理。 */
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

/** 功能：函数 getEntityPatchHeadline，负责 getEntityPatchHeadline 相关处理。 */
export function getEntityPatchHeadline(update: EntityLikeUpdate): string {
  return `${resolveEntityName(update)} · ${resolveFieldName(update)} · ${update.op}`
}

/** 功能：函数 getEntityPatchDetail，负责 getEntityPatchDetail 相关处理。 */
export function getEntityPatchDetail(update: EntityLikeUpdate): string {
  const before = 'before' in update ? update.before : null
  const after = 'after' in update ? update.after : null
  const value = 'value' in update ? update.value : null
  if (after != null || before != null) {
    return `${formatEntityPatchValue(before)} → ${formatEntityPatchValue(after)}`
  }
  return formatEntityPatchValue(value)
}

/** 功能：函数 getEntityPatchChangeSummary，负责 getEntityPatchChangeSummary 相关处理。 */
export function getEntityPatchChangeSummary(update: EntityLikeUpdate, maxLength = 80): string {
  const fieldLabel = getEntityPatchFieldLabel(update)
  const before = 'before' in update ? update.before : null
  const after = 'after' in update ? update.after : null
  const value = 'value' in update ? update.value : null

  if (update.op === 'remove') {
    const removedValue = before ?? value ?? after
    return `${fieldLabel}：移除 ${compactText(formatEntityPatchValue(removedValue), maxLength)}`
  }

  if (before != null || after != null) {
    return `${fieldLabel}：${compactText(formatEntityPatchValue(before), maxLength)} -> ${compactText(formatEntityPatchValue(after), maxLength)}`
  }

  if (value != null) {
    return `${fieldLabel}：${compactText(formatEntityPatchValue(value), maxLength)}`
  }

  return `${fieldLabel}：${getEntityPatchOperationLabel(update.op)}`
}

/** 功能：函数 getEntityPatchEventId，负责 getEntityPatchEventId 相关处理。 */
export function getEntityPatchEventId(update: EntityLikeUpdate): string {
  return 'event_id' in update ? update.event_id : update.eventId
}

/** 功能：函数 getEntityPatchSourceTurn，负责 getEntityPatchSourceTurn 相关处理。 */
export function getEntityPatchSourceTurn(update: EntityLikeUpdate): number | null {
  return isApiEntityUpdate(update) ? (update.source_turn ?? null) : (update.sourceTurn ?? null)
}

/** 功能：函数 getEntityPatchCommittedAt，负责 getEntityPatchCommittedAt 相关处理。 */
export function getEntityPatchCommittedAt(update: EntityLikeUpdate): string {
  return 'committed_at' in update ? update.committed_at : update.committedAt
}

/** 功能：函数 getEntityPatchEvidenceText，负责 getEntityPatchEvidenceText 相关处理。 */
export function getEntityPatchEvidenceText(update: EntityLikeUpdate): string | null {
  return isApiEntityUpdate(update) ? (update.evidence_text ?? null) : (update.evidenceText ?? null)
}

/** 功能：函数 extractWorldUpdateHighlights，负责 extractWorldUpdateHighlights 相关处理。 */
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
