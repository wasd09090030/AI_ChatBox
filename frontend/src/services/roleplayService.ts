/**
 * Roleplay API Service
 * Covers: Personas only
 */

import apiClient from './api'

export interface PersonaProfile {
  id: string
  name: string
  description: string
  title: string | null
  traits: string[]
  metadata: Record<string, unknown>
  created_at: string
  updated_at: string
}

export type PersonaCreate = Omit<PersonaProfile, 'id' | 'created_at' | 'updated_at'>
export type PersonaUpdate = Partial<PersonaCreate>

// ── Character Cards ──────────────────────────────────────────────────────

export const roleplayApi = {
  listPersonas: () =>
    apiClient.get<PersonaProfile[]>('/roleplay/personas').then((r) => r.data),

  getPersona: (id: string) =>
    apiClient.get<PersonaProfile>(`/roleplay/personas/${id}`).then((r) => r.data),

  createPersona: (data: PersonaCreate) =>
    apiClient.post<PersonaProfile>('/roleplay/personas', data).then((r) => r.data),

  updatePersona: (id: string, data: PersonaUpdate) =>
    apiClient.put<PersonaProfile>(`/roleplay/personas/${id}`, data).then((r) => r.data),

  deletePersona: (id: string) =>
    apiClient
      .delete<{ success: boolean; persona_id: string }>(`/roleplay/personas/${id}`)
      .then((r) => r.data),
}
