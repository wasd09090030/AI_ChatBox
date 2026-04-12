/**
 * 文件说明：前端业务域逻辑与接口封装。
 */

import { storage } from '@/utils/storage'
import type { APIKeys, UserConfig } from '@/utils/types'

export type ConfigPersistState = {
  config: UserConfig
  apiKeys: APIKeys
}

// 变量作用：变量 CONFIG_STORAGE_KEYS，用于 CONFIG STORAGE KEYS 相关配置或状态。
export const CONFIG_STORAGE_KEYS = {
  config: 'user_config_v2',
  apiKeys: 'api_keys_v2',
} as const

/** 功能：函数 loadConfigState，负责 loadConfigState 相关处理。 */
export async function loadConfigState(
  fallbackConfig: UserConfig,
  fallbackApiKeys: APIKeys
): Promise<ConfigPersistState> {
  let storedConfig = await storage.getStorage(CONFIG_STORAGE_KEYS.config)
  // api_keys excluded from remote sync intentionally — never pull remotely
  const storedApiKeys = await storage.getStorage(CONFIG_STORAGE_KEYS.apiKeys)

  if (!storedConfig) storedConfig = await storage.pullFromRemote(CONFIG_STORAGE_KEYS.config)

  return {
    config: storedConfig ? { ...fallbackConfig, ...JSON.parse(storedConfig) } : fallbackConfig,
    apiKeys: storedApiKeys ? { ...fallbackApiKeys, ...JSON.parse(storedApiKeys) } : fallbackApiKeys,
  }
}

/** 功能：函数 persistConfig，负责 persistConfig 相关处理。 */
export async function persistConfig(config: UserConfig) {
  await storage.setStorage(CONFIG_STORAGE_KEYS.config, JSON.stringify(config))
  return config
}

/** 功能：函数 persistApiKeys，负责 persistApiKeys 相关处理。 */
export async function persistApiKeys(apiKeys: APIKeys) {
  await storage.setStorage(CONFIG_STORAGE_KEYS.apiKeys, JSON.stringify(apiKeys))
  return apiKeys
}