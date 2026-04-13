/**
 * 文件说明：前端状态管理与会话数据维护。
 */

﻿/**
 * Config Store
 *
 * Manages application configuration and settings (本地持久化版本)
 * Supports: OpenAI, Anthropic, DeepSeek, Qwen, Gemini, Custom
 */

import { defineStore } from 'pinia'
import { ref, computed, watch } from 'vue'
import type {
  APIKeys,
  ProviderBaseUrls,
  ProviderKey,
  SceneModelKey,
  SceneModelPreferences,
  UserConfig,
} from '@/utils/types'
import {
  fetchConfigState,
  usePersistConfigMutation,
  usePersistApiKeysMutation,
} from '@/domains/settings/queries/useConfigPersistence'
import {
  createEmptySceneModelPreferences,
  fetchSceneModelPreferences,
  saveSceneModelPreferences,
} from '@/domains/settings/api/sceneModelApi'
import {
  fetchDefaultProviderSelection,
  saveDefaultProviderSelection,
} from '@/domains/settings/api/providerConfigApi'
import { storage } from '@/utils/storage'

// 常量 BASE_URLS_STORAGE_KEY。
const BASE_URLS_STORAGE_KEY = 'provider_base_urls_v1'

// useConfigStore 状态仓库实例。
export const useConfigStore = defineStore('config', () => {
  // ── State ────────────────────────────────────────────────────────────────
  const config = ref<UserConfig>({
    theme: 'system',
    defaultProvider: 'deepseek',
    defaultModel: 'deepseek-chat',
    temperature: 0.7,
    maxTokens: 2000,
  })

  const apiKeys = ref<APIKeys>({
    openai: undefined,
    anthropic: undefined,
    deepseek: undefined,
    qwen: undefined,
    gemini: undefined,
    custom: undefined,
  })

  /** Custom base URL overrides. Empty string = use provider default. */
  const providerBaseUrls = ref<ProviderBaseUrls>({
    openai: '',
    anthropic: '',
    deepseek: '',
    qwen: '',
    gemini: '',
    custom: '',
  })

  const isLoading = ref(false)
  const error = ref<string | null>(null)
  const sceneModelPreferences = ref<SceneModelPreferences>(createEmptySceneModelPreferences())
  const sceneModelsLoading = ref(false)

  const persistConfigMutation = usePersistConfigMutation()
  const persistApiKeysMutation = usePersistApiKeysMutation()

  function getErrorMessage(err: unknown, fallback: string) {
    if (err instanceof Error && err.message) return err.message
    return fallback
  }

  async function persistConfigState() {
    await persistConfigMutation.mutateAsync(config.value)
  }

  async function persistApiKeysState() {
    await persistApiKeysMutation.mutateAsync(apiKeys.value)
  }

  async function persistBaseUrlsState() {
    await storage.setStorage(BASE_URLS_STORAGE_KEY, JSON.stringify(providerBaseUrls.value))
  }

  // ── Computed ─────────────────────────────────────────────────────────────
  const isDarkMode = computed(() => {
    if (config.value.theme === 'system') {
      return window.matchMedia('(prefers-color-scheme: dark)').matches
    }
    return config.value.theme === 'dark'
  })

  const hasOpenAIKey    = computed(() => !!apiKeys.value.openai)
  const hasAnthropicKey = computed(() => !!apiKeys.value.anthropic)
  const hasDeepSeekKey  = computed(() => !!apiKeys.value.deepseek)
  const hasQwenKey      = computed(() => !!apiKeys.value.qwen)
  const hasGeminiKey    = computed(() => !!apiKeys.value.gemini)
  const hasCustomKey    = computed(() => !!apiKeys.value.custom)
  const hasAnyKey       = computed(() =>
    hasOpenAIKey.value || hasAnthropicKey.value || hasDeepSeekKey.value ||
    hasQwenKey.value   || hasGeminiKey.value    || hasCustomKey.value
  )

  const configuredProviders = computed<ProviderKey[]>(() =>
    (Object.keys(apiKeys.value) as ProviderKey[]).filter(k => !!apiKeys.value[k])
  )

  // Watch theme changes
  watch(isDarkMode, (dark) => {
    document.documentElement.classList.toggle('dark', dark)
  }, { immediate: false })

  // ── Actions ──────────────────────────────────────────────────────────────

  /** Initialize config from local storage */
  async function initializeConfig() {
    try {
      isLoading.value = true

      const state = await fetchConfigState(config.value, apiKeys.value)
      config.value  = state.config
      apiKeys.value = state.apiKeys

      // Load base URL overrides
      let storedBaseUrls = await storage.getStorage(BASE_URLS_STORAGE_KEY)
      if (!storedBaseUrls) {
        // Seed an empty local+remote record on first run so this optional key
        // does not trigger a noisy 404 pull from client-storage.
        storedBaseUrls = JSON.stringify(providerBaseUrls.value)
        await storage.setStorage(BASE_URLS_STORAGE_KEY, storedBaseUrls)
      }
      if (storedBaseUrls) {
        providerBaseUrls.value = {
          ...providerBaseUrls.value,
          ...JSON.parse(storedBaseUrls),
        }
      }

      // Apply theme
      document.documentElement.classList.toggle('dark', isDarkMode.value)

      try {
        const defaultSelection = await fetchDefaultProviderSelection()
        config.value.defaultProvider = defaultSelection.provider
        config.value.defaultModel = defaultSelection.model
      } catch (defaultSelectionError) {
        console.warn('Failed to load default provider selection:', defaultSelectionError)
      }

      try {
        sceneModelsLoading.value = true
        sceneModelPreferences.value = await fetchSceneModelPreferences()
      } catch (sceneError) {
        console.warn('Failed to load scene model preferences:', sceneError)
      } finally {
        sceneModelsLoading.value = false
      }
    } catch (e) {
      console.error('Failed to initialize config:', e)
    } finally {
      isLoading.value = false
    }
  }

  async function setTheme(theme: 'light' | 'dark' | 'system') {
    config.value.theme = theme
    await persistConfigState()
  }

  async function setDefaultProvider(provider: ProviderKey) {
    await setDefaultSelection(provider, config.value.defaultModel)
  }

  async function setDefaultModel(model: string) {
    await setDefaultSelection(config.value.defaultProvider, model)
  }

  async function setDefaultSelection(provider: ProviderKey, model: string) {
    const response = await saveDefaultProviderSelection({ provider, model })
    config.value.defaultProvider = response.provider
    config.value.defaultModel = response.model
    await persistConfigState()
  }

  async function setTemperature(temperature: number) {
    config.value.temperature = Math.max(0, Math.min(2, temperature))
    await persistConfigState()
  }

  async function setMaxTokens(maxTokens: number) {
    config.value.maxTokens = Math.max(1, Math.min(32000, maxTokens))
    await persistConfigState()
  }

  /**
   * Save API key preview (frontend stores masked version; actual key sent to backend).
   * The store holds a masked preview so UI can show "sk-...xxxx" status.
   */
  async function saveAPIKey(provider: ProviderKey, key: string) {
    try {
      error.value = null
      const trimmed = key.trim()
      // Store masked preview only
      apiKeys.value[provider] = trimmed.length > 8
        ? trimmed.substring(0, 4) + '...' + trimmed.substring(trimmed.length - 4)
        : '****'
      await persistApiKeysState()
    } catch (e: unknown) {
      error.value = getErrorMessage(e, 'Failed to save API key')
      throw e
    }
  }

  async function deleteAPIKey(provider: ProviderKey) {
    try {
      error.value = null
      apiKeys.value[provider] = undefined
      await persistApiKeysState()
    } catch (e: unknown) {
      error.value = getErrorMessage(e, 'Failed to delete API key')
      throw e
    }
  }

  /**
   * Save custom base URL for a provider.
   * Pass "" to reset to provider default.
   */
  async function saveBaseUrl(provider: ProviderKey, url: string) {
    providerBaseUrls.value[provider] = url.trim()
    await persistBaseUrlsState()
  }

  async function resetConfig() {
    config.value = {
      theme: 'system',
      defaultProvider: 'deepseek',
      defaultModel: 'deepseek-chat',
      temperature: 0.7,
      maxTokens: 2000,
    }
    await persistConfigState()
  }

  async function refreshSceneModelPreferences() {
    sceneModelsLoading.value = true
    try {
      sceneModelPreferences.value = await fetchSceneModelPreferences()
      return sceneModelPreferences.value
    } finally {
      sceneModelsLoading.value = false
    }
  }

  async function saveSceneModels(preferences: SceneModelPreferences) {
    sceneModelPreferences.value = await saveSceneModelPreferences(preferences)
    return sceneModelPreferences.value
  }

  function getResolvedSceneModel(scene: SceneModelKey) {
    const scenePreference = sceneModelPreferences.value[scene]
    const provider = scenePreference.provider || config.value.defaultProvider || ''
    const model = scenePreference.model || config.value.defaultModel || ''
    return {
      provider: provider || undefined,
      model: model || undefined,
      base_url: provider ? (providerBaseUrls.value[provider] || undefined) : undefined,
    }
  }

  async function exportData() {
    return JSON.stringify({ config: config.value, timestamp: Date.now() }, null, 2)
  }

  async function importData(jsonData: string) {
    try {
      const data = JSON.parse(jsonData)
      if (data.config) {
        config.value = { ...config.value, ...data.config }
        await persistConfigState()
      }
    } catch {
      error.value = 'Invalid import data'
      throw new Error('Invalid import data')
    }
  }

  /** @deprecated — keys managed by backend; kept for compatibility */
  function getAPIKey(_provider: ProviderKey): string | undefined {
    return undefined
  }

  return {
    // State
    config,
    apiKeys,
    providerBaseUrls,
    isLoading,
    error,
    sceneModelPreferences,
    sceneModelsLoading,

    // Computed
    isDarkMode,
    hasOpenAIKey,
    hasAnthropicKey,
    hasDeepSeekKey,
    hasQwenKey,
    hasGeminiKey,
    hasCustomKey,
    hasAnyKey,
    configuredProviders,

    // Actions
    initializeConfig,
    setTheme,
    setDefaultProvider,
    setDefaultModel,
    setDefaultSelection,
    setTemperature,
    setMaxTokens,
    saveAPIKey,
    deleteAPIKey,
    saveBaseUrl,
    getAPIKey,
    resetConfig,
    refreshSceneModelPreferences,
    saveSceneModels,
    getResolvedSceneModel,
    exportData,
    importData,
  }
})
