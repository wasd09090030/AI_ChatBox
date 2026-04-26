/**
 * 文件说明：前端业务域逻辑与接口封装。
 */

import api from '@/services/api'
import type { SceneModelPreference, SceneModelPreferences } from '@/utils/types'

interface SceneModelPreferencesResponse {
  story_generation?: Partial<SceneModelPreference> | null
  input_enhancement?: Partial<SceneModelPreference> | null
  story_adjustment?: Partial<SceneModelPreference> | null
  fallback?: {
    default_model?: string | null
  } | null
}

/** 处理 normalizePreference 相关逻辑。 */
function normalizePreference(value?: Partial<SceneModelPreference> | null): SceneModelPreference {
  const provider = typeof value?.provider === 'string' ? value.provider : ''
  const model = typeof value?.model === 'string' ? value.model : ''
  return {
    provider: provider || '',
    model: model || '',
  }
}

/** 处理 createEmptySceneModelPreferences 相关逻辑。 */
export function createEmptySceneModelPreferences(): SceneModelPreferences {
  return {
    story_generation: { provider: '', model: '' },
    input_enhancement: { provider: '', model: '' },
    story_adjustment: { provider: '', model: '' },
  }
}

/** 处理 fetchSceneModelPreferences 相关逻辑。 */
export async function fetchSceneModelPreferences(): Promise<SceneModelPreferences> {
  const response = await api.get<SceneModelPreferencesResponse>('/providers/scene-models')

  return {
    story_generation: normalizePreference(response.data.story_generation),
    input_enhancement: normalizePreference(response.data.input_enhancement),
    story_adjustment: normalizePreference(response.data.story_adjustment),
  }
}

/** 处理 saveSceneModelPreferences 相关逻辑。 */
export async function saveSceneModelPreferences(
  preferences: SceneModelPreferences,
): Promise<SceneModelPreferences> {
  const response = await api.put<SceneModelPreferencesResponse>('/providers/scene-models', preferences)

  return {
    story_generation: normalizePreference(response.data.story_generation),
    input_enhancement: normalizePreference(response.data.input_enhancement),
    story_adjustment: normalizePreference(response.data.story_adjustment),
  }
}
