/**
 * TanStack Query hooks for Roleplay Personas
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/vue-query'
import {
  roleplayApi,
  type PersonaCreate,
  type PersonaUpdate,
} from '@/services/roleplayService'

// 常量 ROLEPLAY_KEYS。
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

/** 处理 useCreatePersonaMutation 相关逻辑。 */
export function useCreatePersonaMutation() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: PersonaCreate) => roleplayApi.createPersona(data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ROLEPLAY_KEYS.personas }),
  })
}

/** 处理 useUpdatePersonaMutation 相关逻辑。 */
export function useUpdatePersonaMutation() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: PersonaUpdate }) =>
      roleplayApi.updatePersona(id, data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ROLEPLAY_KEYS.personas }),
  })
}

/** 处理 useDeletePersonaMutation 相关逻辑。 */
export function useDeletePersonaMutation() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => roleplayApi.deletePersona(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ROLEPLAY_KEYS.personas }),
  })
}
