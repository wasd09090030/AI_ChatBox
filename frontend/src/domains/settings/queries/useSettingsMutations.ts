/**
 * 文件说明：前端业务域逻辑与接口封装。
 */

import { useMutation } from '@tanstack/vue-query'
import { useConfigStore } from '@/stores/config'
import { useRoleStore } from '@/stores/role'
import { useStorySessionStore } from '@/stores/storySession'

export type ApiKeyProvider = 'openai' | 'anthropic' | 'deepseek'
export type ThemeMode = 'light' | 'dark' | 'system'

/** 处理 useSetThemeMutation 相关逻辑。 */
export function useSetThemeMutation() {
  const configStore = useConfigStore()
  return useMutation({
    mutationFn: async (theme: ThemeMode) => configStore.setTheme(theme),
  })
}

/** 处理 useSetDefaultModelMutation 相关逻辑。 */
export function useSetDefaultModelMutation() {
  const configStore = useConfigStore()
  return useMutation({
    mutationFn: async (model: string) => configStore.setDefaultModel(model),
  })
}

/** 处理 useSetTemperatureMutation 相关逻辑。 */
export function useSetTemperatureMutation() {
  const configStore = useConfigStore()
  return useMutation({
    mutationFn: async (value: number) => configStore.setTemperature(value),
  })
}

/** 处理 useSetMaxTokensMutation 相关逻辑。 */
export function useSetMaxTokensMutation() {
  const configStore = useConfigStore()
  return useMutation({
    mutationFn: async (value: number) => configStore.setMaxTokens(value),
  })
}

/** 处理 useSaveApiKeyMutation 相关逻辑。 */
export function useSaveApiKeyMutation() {
  const configStore = useConfigStore()
  return useMutation({
    mutationFn: async (payload: { provider: ApiKeyProvider; key: string }) =>
      configStore.saveAPIKey(payload.provider, payload.key),
  })
}

/** 处理 useDeleteApiKeyMutation 相关逻辑。 */
export function useDeleteApiKeyMutation() {
  const configStore = useConfigStore()
  return useMutation({
    mutationFn: async (provider: ApiKeyProvider) => configStore.deleteAPIKey(provider),
  })
}

/** 处理 useClearAllDataMutation 相关逻辑。 */
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

/** 处理 useExportDataMutation 相关逻辑。 */
export function useExportDataMutation() {
  const configStore = useConfigStore()
  return useMutation({
    mutationFn: async () => configStore.exportData(),
  })
}
