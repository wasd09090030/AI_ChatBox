import { computed, unref, type MaybeRef } from 'vue'
import { useMutation, useQuery, useQueryClient } from '@tanstack/vue-query'
import {
  scriptDesignApi,
  type ScriptDesignCreateInput,
  type ScriptDesignStatus,
  type ScriptDesignUpdateInput,
} from '@/domains/story/api/scriptDesignApi'

export const SCRIPT_DESIGN_KEYS = {
  all: ['script-designs'] as const,
  lists: () => ['script-designs', 'list'] as const,
  list: (worldId?: string, status?: ScriptDesignStatus) => ['script-designs', 'list', worldId ?? 'all', status ?? 'all'] as const,
  detail: (id?: string) => ['script-designs', 'detail', id ?? 'none'] as const,
  bindings: (id?: string) => ['script-designs', 'bindings', id ?? 'none'] as const,
}

export function useScriptDesignsQuery(
  worldId?: MaybeRef<string | undefined>,
  status?: MaybeRef<ScriptDesignStatus | undefined>,
) {
  return useQuery({
    queryKey: computed(() => SCRIPT_DESIGN_KEYS.list(unref(worldId) || undefined, unref(status) || undefined)),
    queryFn: () => scriptDesignApi.list(unref(worldId) || undefined, unref(status) || undefined),
    enabled: computed(() => !!unref(worldId)),
  })
}

export function useScriptDesignQuery(scriptDesignId?: MaybeRef<string | undefined>) {
  return useQuery({
    queryKey: computed(() => SCRIPT_DESIGN_KEYS.detail(unref(scriptDesignId) || undefined)),
    queryFn: () => scriptDesignApi.get(unref(scriptDesignId) || ''),
    enabled: computed(() => !!unref(scriptDesignId)),
  })
}

export function useScriptDesignBindingsQuery(scriptDesignId?: MaybeRef<string | undefined>) {
  return useQuery({
    queryKey: computed(() => SCRIPT_DESIGN_KEYS.bindings(unref(scriptDesignId) || undefined)),
    queryFn: () => scriptDesignApi.getStoryBindings(unref(scriptDesignId) || ''),
    enabled: computed(() => !!unref(scriptDesignId)),
  })
}

export function useCreateScriptDesignMutation() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (payload: ScriptDesignCreateInput) => scriptDesignApi.create(payload),
    onSuccess: (created) => {
      queryClient.invalidateQueries({ queryKey: SCRIPT_DESIGN_KEYS.lists() })
      queryClient.setQueryData(SCRIPT_DESIGN_KEYS.detail(created.id), created)
    },
  })
}

export function useUpdateScriptDesignMutation() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ id, payload }: { id: string; payload: ScriptDesignUpdateInput }) =>
      scriptDesignApi.update(id, payload),
    onSuccess: (updated) => {
      queryClient.invalidateQueries({ queryKey: SCRIPT_DESIGN_KEYS.lists() })
      queryClient.invalidateQueries({ queryKey: SCRIPT_DESIGN_KEYS.bindings(updated.id) })
      queryClient.setQueryData(SCRIPT_DESIGN_KEYS.detail(updated.id), updated)
    },
  })
}

export function useDeleteScriptDesignMutation() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (scriptDesignId: string) => scriptDesignApi.remove(scriptDesignId),
    onSuccess: (_result, scriptDesignId) => {
      queryClient.invalidateQueries({ queryKey: SCRIPT_DESIGN_KEYS.lists() })
      queryClient.removeQueries({ queryKey: SCRIPT_DESIGN_KEYS.detail(scriptDesignId) })
      queryClient.removeQueries({ queryKey: SCRIPT_DESIGN_KEYS.bindings(scriptDesignId) })
    },
  })
}