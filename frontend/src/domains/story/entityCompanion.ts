import type { EntityCompanion } from '@/domains/story/api/storyGenerationApi'

type LooseCompanionObject = {
  id?: unknown
  display_name?: unknown
}

function isCompanionObject(value: unknown): value is LooseCompanionObject {
  return typeof value === 'object' && value !== null
}

/** 返回同行者引用中的实体 ID。 */
export function getEntityCompanionId(companion: EntityCompanion | unknown): string | null {
  if (typeof companion === 'string') {
    const normalizedId = companion.trim()
    return normalizedId || null
  }
  if (!isCompanionObject(companion)) return null
  const rawId = typeof companion.id === 'string' ? companion.id : ''
  const normalizedId = rawId.trim()
  return normalizedId || null
}

/** 优先返回同行者自带的显示名。 */
export function getEntityCompanionDisplayName(companion: EntityCompanion | unknown): string | null {
  if (!isCompanionObject(companion)) return null
  const rawDisplayName = typeof companion.display_name === 'string' ? companion.display_name : ''
  const displayName = rawDisplayName.trim()
  return displayName || null
}

/** 统一解析同行者展示文案，兼容 string / object 两种结构。 */
export function getEntityCompanionLabel(
  companion: EntityCompanion | unknown,
  entityNameMap?: Map<string, string>,
): string {
  const displayName = getEntityCompanionDisplayName(companion)
  if (displayName) return displayName

  const companionId = getEntityCompanionId(companion)
  if (!companionId) return '未知同行者'
  return entityNameMap?.get(companionId) ?? companionId
}
