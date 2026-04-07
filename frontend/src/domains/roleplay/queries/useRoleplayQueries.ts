/**
 * TanStack Query hooks for Roleplay Personas
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/vue-query'
import {
  roleplayApi,
  type PersonaCreate,
  type PersonaUpdate,
} from '@/services/roleplayService'

export const ROLEPLAY_KEYS = {
  personas: ['roleplay', 'personas'] as const,
  persona: (id: string) => ['roleplay', 'personas', id] as const,
}

// ── Personas ─────────────────────────────────────────────────────────────

export function usePersonasQuery() {
  return useQuery({
    queryKey: ROLEPLAY_KEYS.personas,
    queryFn: roleplayApi.listPersonas,
  })
}

export function useCreatePersonaMutation() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: PersonaCreate) => roleplayApi.createPersona(data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ROLEPLAY_KEYS.personas }),
  })
}

export function useUpdatePersonaMutation() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: PersonaUpdate }) =>
      roleplayApi.updatePersona(id, data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ROLEPLAY_KEYS.personas }),
  })
}

export function useDeletePersonaMutation() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => roleplayApi.deletePersona(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ROLEPLAY_KEYS.personas }),
  })
}
