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

function normalizePreference(value?: Partial<SceneModelPreference> | null): SceneModelPreference {
  const provider = typeof value?.provider === 'string' ? value.provider : ''
  const model = typeof value?.model === 'string' ? value.model : ''
  return {
    provider: provider || '',
    model: model || '',
  }
}

export function createEmptySceneModelPreferences(): SceneModelPreferences {
  return {
    story_generation: { provider: '', model: '' },
    input_enhancement: { provider: '', model: '' },
    story_adjustment: { provider: '', model: '' },
  }
}

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
