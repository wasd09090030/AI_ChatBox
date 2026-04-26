/**
 * 文件说明：前端业务域逻辑与接口封装。
 */

import api from '@/services/api'
import { fetchAvailableModels, type FetchModelsResult, type ModelInfo } from '@/services/fetchAvailableModels'
import { testApiConnection, type TestConnectionResult } from '@/services/testApiConnection'
import type { ProviderKey } from '@/utils/types'

/** 处理 saveProviderConfig 相关逻辑。 */
export async function saveProviderConfig(options: {
  provider: ProviderKey
  apiKey?: string
  baseUrl?: string
}): Promise<void> {
  await api.post(
    '/providers/config',
    {
      provider: options.provider,
      api_key: options.apiKey ?? undefined,
      base_url: options.baseUrl ?? undefined,
    },
  )
}

/** 处理 fetchDefaultProviderSelection 相关逻辑。 */
export async function fetchDefaultProviderSelection(): Promise<{ provider: ProviderKey; model: string }> {
  const response = await api.get<{ provider: ProviderKey; model: string }>('/providers/default-selection')
  return response.data
}

/** 处理 saveDefaultProviderSelection 相关逻辑。 */
export async function saveDefaultProviderSelection(options: {
  provider: ProviderKey
  model: string
}): Promise<{ provider: ProviderKey; model: string }> {
  const response = await api.put<{ provider: ProviderKey; model: string }>('/providers/default-selection', options)
  return response.data
}

export { fetchAvailableModels, testApiConnection }
export type { FetchModelsResult, ModelInfo, TestConnectionResult }
