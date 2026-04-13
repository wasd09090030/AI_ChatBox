/**
 * 文件说明：前端业务域逻辑与接口封装。
 */

import { useMutation } from '@tanstack/vue-query'
import { queryClient } from '@/app/queryClient'
import type { APIKeys, UserConfig } from '@/utils/types'
import {
  loadConfigState,
  persistConfig,
  persistApiKeys,
  type ConfigPersistState,
} from '../api/configStorageApi'

// 常量 SETTINGS_QUERY_KEYS。
export const SETTINGS_QUERY_KEYS = {
  configState: ['settings', 'config-state'] as const,
}

/** 处理 fetchConfigState 相关逻辑。 */
export async function fetchConfigState(fallbackConfig: UserConfig, fallbackApiKeys: APIKeys) {
  return queryClient.fetchQuery({
    queryKey: SETTINGS_QUERY_KEYS.configState,
    queryFn: async () => loadConfigState(fallbackConfig, fallbackApiKeys),
    staleTime: 15 * 1000,
  })
}

/** 处理 usePersistConfigMutation 相关逻辑。 */
export function usePersistConfigMutation() {
  return useMutation({
    mutationFn: persistConfig,
    onSuccess: (config) => {
      const previous = queryClient.getQueryData<ConfigPersistState>(SETTINGS_QUERY_KEYS.configState)
      queryClient.setQueryData(SETTINGS_QUERY_KEYS.configState, {
        config,
        apiKeys: previous?.apiKeys ?? {
          openai: undefined,
          anthropic: undefined,
          deepseek: undefined,
          qwen: undefined,
          gemini: undefined,
          custom: undefined,
        },
      })
    },
  })
}

/** 处理 usePersistApiKeysMutation 相关逻辑。 */
export function usePersistApiKeysMutation() {
  return useMutation({
    mutationFn: persistApiKeys,
    onSuccess: (apiKeys) => {
      const previous = queryClient.getQueryData<ConfigPersistState>(SETTINGS_QUERY_KEYS.configState)
      queryClient.setQueryData(SETTINGS_QUERY_KEYS.configState, {
        config: previous?.config ?? {
          theme: 'system',
          defaultProvider: 'deepseek',
          defaultModel: 'deepseek-chat',
          temperature: 0.7,
          maxTokens: 2000,
        },
        apiKeys,
      })
    },
  })
}