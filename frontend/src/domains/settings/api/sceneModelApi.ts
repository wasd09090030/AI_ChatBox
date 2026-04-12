/**
 * 文件说明：前端业务域逻辑与接口封装。
 */

import api from '@/services/api'
import { getUserHeaders } from '@/domains/user/api/userIdentity'
import type { SceneModelPreference, SceneModelPreferences } from '@/utils/types'

interface SceneModelPreferencesResponse {
  story_generation?: Partial<SceneModelPreference> | null
  input_enhancement?: Partial<SceneModelPreference> | null
  story_adjustment?: Partial<SceneModelPreference> | null
  fallback?: {
    default_model?: string | null
  } | null
}

/** 功能：函数 normalizePreference，负责 normalizePreference 相关处理。 */
function normalizePreference(value?: Partial<SceneModelPreference> | null): SceneModelPreference {
  const provider = typeof value?.provider === 'string' ? value.provider : ''
  const model = typeof value?.model === 'string' ? value.model : ''
  return {
    provider: provider || '',
    model: model || '',
  }
}

/** 功能：函数 createEmptySceneModelPreferences，负责 createEmptySceneModelPreferences 相关处理。 */
export function createEmptySceneModelPreferences(): SceneModelPreferences {
  return {
    story_generation: { provider: '', model: '' },
    input_enhancement: { provider: '', model: '' },
    story_adjustment: { provider: '', model: '' },
  }
}

/** 功能：函数 fetchSceneModelPreferences，负责 fetchSceneModelPreferences 相关处理。 */
export async function fetchSceneModelPreferences(): Promise<SceneModelPreferences> {
  const response = await api.get<SceneModelPreferencesResponse>('/providers/scene-models', {
    headers: getUserHeaders(),
  })

  return {
    story_generation: normalizePreference(response.data.story_generation),
    input_enhancement: normalizePreference(response.data.input_enhancement),
    story_adjustment: normalizePreference(response.data.story_adjustment),
  }
}

/** 功能：函数 saveSceneModelPreferences，负责 saveSceneModelPreferences 相关处理。 */
export async function saveSceneModelPreferences(
  preferences: SceneModelPreferences,
): Promise<SceneModelPreferences> {
  const response = await api.put<SceneModelPreferencesResponse>(
    '/providers/scene-models',
    preferences,
    {
      headers: getUserHeaders(),
    },
  )

  return {
    story_generation: normalizePreference(response.data.story_generation),
    input_enhancement: normalizePreference(response.data.input_enhancement),
    story_adjustment: normalizePreference(response.data.story_adjustment),
  }
}
