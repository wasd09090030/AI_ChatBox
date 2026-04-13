/**
 * 文件说明：前端业务域逻辑与接口封装。
 */

import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useToast } from '@/components/ui/toast'
import { PROVIDERS, resolveToneInfo } from '@/domains/settings/constants/providerCatalog'
import {
  fetchAvailableModels,
  saveProviderConfig,
  testApiConnection,
  type ModelInfo,
  type TestConnectionResult,
} from '@/domains/settings/api/providerConfigApi'
import { useConfigStore } from '@/stores/config'
import { useRagStoryStore } from '@/stores/ragStory'
import type { ProviderKey } from '@/utils/types'

// 常量 LS_REMOTE_MODELS_KEY。
const LS_REMOTE_MODELS_KEY = 'provider_remote_models_v1'
// 常量 LS_SELECTED_MODELS_KEY。
const LS_SELECTED_MODELS_KEY = 'provider_selected_models_v1'

/** 处理 useDashboardConfig 相关逻辑。 */
export function useDashboardConfig() {
  const { toast } = useToast()
  const configStore = useConfigStore()
  const ragStoryStore = useRagStoryStore()

  const currentToneInfo = computed(() => {
    const world = ragStoryStore.currentWorld
    if (!world) return null
    const tone = ((world as Record<string, unknown>).narrative_tone as string || '').trim()
    return tone ? resolveToneInfo(tone) : null
  })

  const effectiveTemp = computed(() => {
    const base = configStore.config.temperature
    const offset = currentToneInfo.value?.offset ?? 0
    return Math.max(0.3, Math.min(1.5, base + offset))
  })
  const currentWorldName = computed(() => ragStoryStore.currentWorld?.name ?? '')

  const keyInputs = reactive<Record<ProviderKey, string>>({
    deepseek: '', qwen: '', openai: '', gemini: '', anthropic: '', custom: '',
  })
  const baseUrlInputs = reactive<Record<ProviderKey, string>>({
    deepseek: '', qwen: '', openai: '', gemini: '', anthropic: '', custom: '',
  })
  const showKey = reactive<Record<ProviderKey, boolean>>({
    deepseek: false, qwen: false, openai: false, gemini: false, anthropic: false, custom: false,
  })
  const showAdvanced = reactive<Record<ProviderKey, boolean>>({
    deepseek: false, qwen: false, openai: false, gemini: false, anthropic: false, custom: false,
  })
  const saving = reactive<Record<ProviderKey, boolean>>({
    deepseek: false, qwen: false, openai: false, gemini: false, anthropic: false, custom: false,
  })
  const testing = reactive<Record<ProviderKey, boolean>>({
    deepseek: false, qwen: false, openai: false, gemini: false, anthropic: false, custom: false,
  })
  const testResults = reactive<Record<ProviderKey, TestConnectionResult | null>>({
    deepseek: null, qwen: null, openai: null, gemini: null, anthropic: null, custom: null,
  })
  const fetchingModels = reactive<Record<ProviderKey, boolean>>({
    deepseek: false, qwen: false, openai: false, gemini: false, anthropic: false, custom: false,
  })
  const remoteModels = reactive<Record<ProviderKey, ModelInfo[]>>({
    deepseek: [], qwen: [], openai: [], gemini: [], anthropic: [], custom: [],
  })
  const selectedModels = reactive<Record<ProviderKey, string>>({
    deepseek: PROVIDERS.find((provider) => provider.key === 'deepseek')?.models[0]?.value ?? '',
    qwen: PROVIDERS.find((provider) => provider.key === 'qwen')?.models[0]?.value ?? '',
    openai: PROVIDERS.find((provider) => provider.key === 'openai')?.models[0]?.value ?? '',
    gemini: PROVIDERS.find((provider) => provider.key === 'gemini')?.models[0]?.value ?? '',
    anthropic: PROVIDERS.find((provider) => provider.key === 'anthropic')?.models[0]?.value ?? '',
    custom: '',
  })

  function syncDefaultSelectionIntoProviderModelList() {
    const defaultProvider = configStore.config.defaultProvider as ProviderKey
    if (defaultProvider && configStore.config.defaultModel) {
      selectedModels[defaultProvider] = configStore.config.defaultModel
    }
  }

  syncDefaultSelectionIntoProviderModelList()

  function persistRemoteModels() {
    try {
      localStorage.setItem(LS_REMOTE_MODELS_KEY, JSON.stringify(remoteModels))
    } catch {
      return
    }
  }

  function persistSelectedModels() {
    try {
      localStorage.setItem(LS_SELECTED_MODELS_KEY, JSON.stringify(selectedModels))
    } catch {
      return
    }
  }

  onMounted(() => {
    try {
      const storedRemote = localStorage.getItem(LS_REMOTE_MODELS_KEY)
      if (storedRemote) {
        const parsed = JSON.parse(storedRemote) as Record<string, ModelInfo[]>
        for (const key of Object.keys(parsed) as ProviderKey[]) {
          if (key in remoteModels && parsed[key]?.length) {
            remoteModels[key] = parsed[key]
          }
        }
      }

      const storedSelected = localStorage.getItem(LS_SELECTED_MODELS_KEY)
      if (storedSelected) {
        const parsed = JSON.parse(storedSelected) as Record<string, string>
        for (const key of Object.keys(parsed) as ProviderKey[]) {
          if (key in selectedModels && parsed[key]) {
            selectedModels[key] = parsed[key]
          }
        }
      }
    } catch {
      return
    }

    syncDefaultSelectionIntoProviderModelList()
  })

  watch(selectedModels, persistSelectedModels, { deep: true })
  watch(
    () => [configStore.config.defaultProvider, configStore.config.defaultModel] as const,
    () => {
      syncDefaultSelectionIntoProviderModelList()
    },
  )

  function keyStatus(provider: ProviderKey): string | undefined {
    return configStore.apiKeys[provider]
  }

  function modelsForProvider(provider: ProviderKey): { value: string; label: string }[] {
    const remote = remoteModels[provider]
    if (remote.length) {
      return remote.map((model) => ({ value: model.id, label: model.id }))
    }
    return PROVIDERS.find((item) => item.key === provider)?.models ?? []
  }

  function providerName(key: ProviderKey): string {
    return PROVIDERS.find((provider) => provider.key === key)?.name ?? key
  }

  async function setAsDefault(provider: ProviderKey) {
    const model = selectedModels[provider]
    if (!model) {
      toast({ title: '请先选择一个模型', variant: 'destructive' })
      return
    }
    await configStore.setDefaultSelection(provider, model)
    toast({ title: `已设为默认：${providerName(provider)} / ${model}` })
  }

  const isDefaultProvider = computed(() => configStore.config.defaultProvider as ProviderKey)

  async function testConnection(provider: ProviderKey) {
    if (!keyStatus(provider)) {
      toast({ title: '请先保存 API Key', variant: 'destructive' })
      return
    }
    const baseUrlOverride = baseUrlInputs[provider].trim() || undefined
    testing[provider] = true
    testResults[provider] = null
    try {
      testResults[provider] = await testApiConnection(provider, baseUrlOverride)
    } finally {
      testing[provider] = false
    }
  }

  async function fetchModels(provider: ProviderKey) {
    if (!keyStatus(provider)) {
      toast({ title: '请先保存 API Key', variant: 'destructive' })
      return
    }
    const baseUrlOverride = baseUrlInputs[provider].trim() || undefined
    fetchingModels[provider] = true
    try {
      const result = await fetchAvailableModels(provider, baseUrlOverride)
      if (result.success) {
        remoteModels[provider] = result.models
        persistRemoteModels()
        if (!selectedModels[provider] && result.models.length) {
          selectedModels[provider] = result.models[0]?.id ?? ''
          persistSelectedModels()
        }
        const hint = result.source === 'preset' ? '（预置列表）' : ''
        toast({ title: `获取到 ${result.models.length} 个模型${hint}` })
      } else {
        toast({ title: '获取模型失败', description: result.error, variant: 'destructive' })
      }
    } finally {
      fetchingModels[provider] = false
    }
  }

  async function saveKey(provider: ProviderKey) {
    const apiKey = keyInputs[provider].trim()
    if (!apiKey) return
    saving[provider] = true
    try {
      await saveProviderConfig({ provider, apiKey })
      await configStore.saveAPIKey(provider, apiKey)
      keyInputs[provider] = ''
      toast({ title: `${providerName(provider)} API Key 已保存` })
    } catch (error) {
      console.error(error)
      toast({ title: '保存失败', description: String(error), variant: 'destructive' })
    } finally {
      saving[provider] = false
    }
  }

  async function deleteKey(provider: ProviderKey) {
    try {
      await saveProviderConfig({ provider, apiKey: '' })
      await configStore.deleteAPIKey(provider)
      toast({ title: `${providerName(provider)} API Key 已删除` })
    } catch (error) {
      toast({ title: '删除失败', description: String(error), variant: 'destructive' })
    }
  }

  async function saveBaseUrl(provider: ProviderKey) {
    const baseUrl = baseUrlInputs[provider].trim()
    try {
      await saveProviderConfig({ provider, baseUrl })
      await configStore.saveBaseUrl(provider, baseUrl)
      toast({ title: baseUrl ? 'Base URL 已保存' : 'Base URL 已重置为默认' })
    } catch (error) {
      toast({ title: '保存 Base URL 失败', description: String(error), variant: 'destructive' })
    }
  }

  function initBaseUrlInput(provider: ProviderKey) {
    if (!baseUrlInputs[provider]) {
      baseUrlInputs[provider] = configStore.providerBaseUrls[provider] || ''
    }
  }

  function toggleAdvanced(provider: ProviderKey) {
    showAdvanced[provider] = !showAdvanced[provider]
    if (showAdvanced[provider]) initBaseUrlInput(provider)
  }

  const tempInput = ref(String(configStore.config.temperature))
  const tempError = ref('')
  function onTempInput(event: Event) {
    const value = (event.target as HTMLInputElement).value
    tempInput.value = value
    const num = parseFloat(value)
    if (isNaN(num) || num < 0 || num > 2) {
      tempError.value = '请输入 0 ~ 2 之间的数值'
    } else {
      tempError.value = ''
      configStore.setTemperature(num)
    }
  }

  const maxTokensInput = ref(String(configStore.config.maxTokens))
  const maxTokensError = ref('')
  function onMaxTokensInput(event: Event) {
    const value = (event.target as HTMLInputElement).value
    maxTokensInput.value = value
    const num = parseInt(value, 10)
    if (isNaN(num) || num < 100 || num > 32000) {
      maxTokensError.value = '请输入 100 ~ 32000 之间的整数'
    } else {
      maxTokensError.value = ''
      configStore.setMaxTokens(num)
    }
  }

  async function resetConfig() {
    await configStore.resetConfig()
    tempInput.value = String(configStore.config.temperature)
    maxTokensInput.value = String(configStore.config.maxTokens)
    syncDefaultSelectionIntoProviderModelList()
    toast({ title: '已恢复默认设置' })
  }

  return {
    configStore,
    currentToneInfo,
    effectiveTemp,
    currentWorldName,
    PROVIDERS,
    keyInputs,
    baseUrlInputs,
    showKey,
    showAdvanced,
    saving,
    testing,
    testResults,
    fetchingModels,
    remoteModels,
    selectedModels,
    persistSelectedModels,
    keyStatus,
    modelsForProvider,
    setAsDefault,
    isDefaultProvider,
    testConnection,
    fetchModels,
    saveKey,
    deleteKey,
    saveBaseUrl,
    toggleAdvanced,
    tempInput,
    tempError,
    onTempInput,
    maxTokensInput,
    maxTokensError,
    onMaxTokensInput,
    resetConfig,
  }
}
