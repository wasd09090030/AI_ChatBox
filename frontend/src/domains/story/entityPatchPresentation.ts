import type { EntityStateUpdate } from '@/domains/story/api/storyGenerationApi'
import type { StoryEntityUpdateRecord, StoryWorldUpdateRecord } from '@/stores/storySession'

type EntityLikeUpdate = EntityStateUpdate | StoryEntityUpdateRecord

function isApiEntityUpdate(update: EntityLikeUpdate): update is EntityStateUpdate {
  return 'entity_name' in update || 'field_name' in update
}

function resolveEntityName(update: EntityLikeUpdate): string {
  if (isApiEntityUpdate(update)) {
    return update.entity_name ?? update.entity_id
  }
  return update.entityName ?? update.entityId
}

function resolveFieldName(update: EntityLikeUpdate): string {
  if (isApiEntityUpdate(update)) {
    return update.field_name
  }
  return update.fieldName
}

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

export function getEntityPatchHeadline(update: EntityLikeUpdate): string {
  return `${resolveEntityName(update)} · ${resolveFieldName(update)} · ${update.op}`
}

export function getEntityPatchDetail(update: EntityLikeUpdate): string {
  const before = 'before' in update ? update.before : null
  const after = 'after' in update ? update.after : null
  const value = 'value' in update ? update.value : null
  if (after != null || before != null) {
    return `${formatEntityPatchValue(before)} → ${formatEntityPatchValue(after)}`
  }
  return formatEntityPatchValue(value)
}

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
