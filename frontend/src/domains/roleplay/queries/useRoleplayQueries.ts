/**
 * TanStack Query hooks for Roleplay Personas
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/vue-query'
import {
  roleplayApi,
  type PersonaCreate,
  type PersonaUpdate,
} from '@/services/roleplayService'

// 变量作用：变量 ROLEPLAY_KEYS，用于 ROLEPLAY KEYS 相关配置或状态。
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

/** 功能：函数 useCreatePersonaMutation，负责 useCreatePersonaMutation 相关处理。 */
export function useCreatePersonaMutation() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: PersonaCreate) => roleplayApi.createPersona(data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ROLEPLAY_KEYS.personas }),
  })
}

/** 功能：函数 useUpdatePersonaMutation，负责 useUpdatePersonaMutation 相关处理。 */
export function useUpdatePersonaMutation() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: PersonaUpdate }) =>
      roleplayApi.updatePersona(id, data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ROLEPLAY_KEYS.personas }),
  })
}

/** 功能：函数 useDeletePersonaMutation，负责 useDeletePersonaMutation 相关处理。 */
export function useDeletePersonaMutation() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => roleplayApi.deletePersona(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ROLEPLAY_KEYS.personas }),
  })
}
