/**
 * 文件说明：前端业务域逻辑与接口封装。
 */

import { useMutation } from '@tanstack/vue-query'
import { useConfigStore } from '@/stores/config'
import { useRoleStore } from '@/stores/role'
import { useStorySessionStore } from '@/stores/storySession'

export type ApiKeyProvider = 'openai' | 'anthropic' | 'deepseek'
export type ThemeMode = 'light' | 'dark' | 'system'

/** 功能：函数 useSetThemeMutation，负责 useSetThemeMutation 相关处理。 */
export function useSetThemeMutation() {
  const configStore = useConfigStore()
  return useMutation({
    mutationFn: async (theme: ThemeMode) => configStore.setTheme(theme),
  })
}

/** 功能：函数 useSetDefaultModelMutation，负责 useSetDefaultModelMutation 相关处理。 */
export function useSetDefaultModelMutation() {
  const configStore = useConfigStore()
  return useMutation({
    mutationFn: async (model: string) => configStore.setDefaultModel(model),
  })
}

/** 功能：函数 useSetTemperatureMutation，负责 useSetTemperatureMutation 相关处理。 */
export function useSetTemperatureMutation() {
  const configStore = useConfigStore()
  return useMutation({
    mutationFn: async (value: number) => configStore.setTemperature(value),
  })
}

/** 功能：函数 useSetMaxTokensMutation，负责 useSetMaxTokensMutation 相关处理。 */
export function useSetMaxTokensMutation() {
  const configStore = useConfigStore()
  return useMutation({
    mutationFn: async (value: number) => configStore.setMaxTokens(value),
  })
}

/** 功能：函数 useSaveApiKeyMutation，负责 useSaveApiKeyMutation 相关处理。 */
export function useSaveApiKeyMutation() {
  const configStore = useConfigStore()
  return useMutation({
    mutationFn: async (payload: { provider: ApiKeyProvider; key: string }) =>
      configStore.saveAPIKey(payload.provider, payload.key),
  })
}

/** 功能：函数 useDeleteApiKeyMutation，负责 useDeleteApiKeyMutation 相关处理。 */
export function useDeleteApiKeyMutation() {
  const configStore = useConfigStore()
  return useMutation({
    mutationFn: async (provider: ApiKeyProvider) => configStore.deleteAPIKey(provider),
  })
}

/** 功能：函数 useClearAllDataMutation，负责 useClearAllDataMutation 相关处理。 */
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

/** 功能：函数 useExportDataMutation，负责 useExportDataMutation 相关处理。 */
export function useExportDataMutation() {
  const configStore = useConfigStore()
  return useMutation({
    mutationFn: async () => configStore.exportData(),
  })
}
