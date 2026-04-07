import { useMutation } from '@tanstack/vue-query'
import { useConfigStore } from '@/stores/config'
import { useRoleStore } from '@/stores/role'
import { useStorySessionStore } from '@/stores/storySession'

export type ApiKeyProvider = 'openai' | 'anthropic' | 'deepseek'
export type ThemeMode = 'light' | 'dark' | 'system'

export function useSetThemeMutation() {
  const configStore = useConfigStore()
  return useMutation({
    mutationFn: async (theme: ThemeMode) => configStore.setTheme(theme),
  })
}

export function useSetDefaultModelMutation() {
  const configStore = useConfigStore()
  return useMutation({
    mutationFn: async (model: string) => configStore.setDefaultModel(model),
  })
}

export function useSetTemperatureMutation() {
  const configStore = useConfigStore()
  return useMutation({
    mutationFn: async (value: number) => configStore.setTemperature(value),
  })
}

export function useSetMaxTokensMutation() {
  const configStore = useConfigStore()
  return useMutation({
    mutationFn: async (value: number) => configStore.setMaxTokens(value),
  })
}

export function useSaveApiKeyMutation() {
  const configStore = useConfigStore()
  return useMutation({
    mutationFn: async (payload: { provider: ApiKeyProvider; key: string }) =>
      configStore.saveAPIKey(payload.provider, payload.key),
  })
}

export function useDeleteApiKeyMutation() {
  const configStore = useConfigStore()
  return useMutation({
    mutationFn: async (provider: ApiKeyProvider) => configStore.deleteAPIKey(provider),
  })
}

export function useClearAllDataMutation() {
  const roleStore = useRoleStore()
  const storySessionStore = useStorySessionStore()

  return useMutation({
    mutationFn: async () => {
      await storySessionStore.clearAll()
      await roleStore.resetToDefaults()
    },
  })
}

export function useExportDataMutation() {
  const configStore = useConfigStore()
  return useMutation({
    mutationFn: async () => configStore.exportData(),
  })
}
