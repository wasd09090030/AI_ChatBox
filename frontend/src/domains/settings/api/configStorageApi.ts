import { storage } from '@/utils/storage'
import type { APIKeys, UserConfig } from '@/utils/types'

export type ConfigPersistState = {
  config: UserConfig
  apiKeys: APIKeys
}

export const CONFIG_STORAGE_KEYS = {
  config: 'user_config_v2',
  apiKeys: 'api_keys_v2',
} as const

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

export async function persistConfig(config: UserConfig) {
  await storage.setStorage(CONFIG_STORAGE_KEYS.config, JSON.stringify(config))
  return config
}

export async function persistApiKeys(apiKeys: APIKeys) {
  await storage.setStorage(CONFIG_STORAGE_KEYS.apiKeys, JSON.stringify(apiKeys))
  return apiKeys
}