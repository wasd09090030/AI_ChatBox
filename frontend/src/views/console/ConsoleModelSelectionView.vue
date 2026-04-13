<script setup lang="ts">
// 文件说明：前端页面级视图编排。
import { BookOpen, FilePenLine, RefreshCw, Save, Sparkles } from 'lucide-vue-next'
import { computed, onMounted, reactive, ref } from 'vue'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Separator } from '@/components/ui/separator'
import { useToast } from '@/components/ui/toast'
import { PROVIDERS } from '@/domains/settings/constants/providerCatalog'
import { fetchAvailableModels, type ModelInfo } from '@/services/fetchAvailableModels'
import { useConfigStore } from '@/stores/config'
import type { ProviderKey, SceneModelKey, SceneModelPreferences } from '@/utils/types'

type SceneCard = {
  key: SceneModelKey
  label: string
  description: string
  icon: typeof BookOpen
}

const SCENE_CARDS: SceneCard[] = [
  {
    key: 'story_generation',
    label: '故事生成',
    description: '控制 StoryView 正式续写时默认使用的 provider 与模型。',
    icon: BookOpen,
  },
  {
    key: 'input_enhancement',
    label: 'Prompt 优化',
    description: '对应 StoryView 中的“AI 增强 Prompt”预览链路。',
    icon: Sparkles,
  },
  {
    key: 'story_adjustment',
    label: '故事调整',
    description: '控制 StoryAdjustment 页面局部润色时使用的 provider 与模型。',
    icon: FilePenLine,
  },
]

// 常量 CUSTOM_MODEL_SENTINEL。
const CUSTOM_MODEL_SENTINEL = '__custom__'

// configStore 状态仓库实例。
const configStore = useConfigStore()
const { toast } = useToast()

// saving 相关状态。
const saving = ref(false)
// loading 相关状态。
const loading = ref(false)
// draftPreferences 相关状态。
const draftPreferences = reactive<SceneModelPreferences>({
  story_generation: { provider: '', model: '' },
  input_enhancement: { provider: '', model: '' },
  story_adjustment: { provider: '', model: '' },
})
// remoteModels 相关状态。
const remoteModels = reactive<Record<ProviderKey, ModelInfo[]>>({
  deepseek: [],
  qwen: [],
  openai: [],
  gemini: [],
  anthropic: [],
  custom: [],
})
// fetchingModels 相关状态。
const fetchingModels = reactive<Record<ProviderKey, boolean>>({
  deepseek: false,
  qwen: false,
  openai: false,
  gemini: false,
  anthropic: false,
  custom: false,
})
// customModelEnabled 相关状态。
const customModelEnabled = reactive<Record<SceneModelKey, boolean>>({
  story_generation: false,
  input_enhancement: false,
  story_adjustment: false,
})

/** 处理 clonePreferences 相关逻辑。 */
function clonePreferences(source: SceneModelPreferences) {
  draftPreferences.story_generation = { ...source.story_generation }
  draftPreferences.input_enhancement = { ...source.input_enhancement }
  draftPreferences.story_adjustment = { ...source.story_adjustment }

  for (const scene of SCENE_CARDS) {
    const provider = draftPreferences[scene.key].provider
    const model = draftPreferences[scene.key].model
    customModelEnabled[scene.key] = provider === 'custom' || (!!model && !modelOptionsForProvider(provider as ProviderKey).some((item) => item.value === model))
  }
}

/** 处理 modelOptionsForProvider 相关逻辑。 */
function modelOptionsForProvider(provider: ProviderKey | '') {
  if (!provider) return []
  const remote = remoteModels[provider]
  if (remote.length) {
    return remote.map((model) => ({ value: model.id, label: model.id }))
  }
  return PROVIDERS.find((item) => item.key === provider)?.models ?? []
}

/** 处理 effectiveFallbackLabel 相关逻辑。 */
function effectiveFallbackLabel(scene: SceneModelKey) {
  const fallback = configStore.getResolvedSceneModel(scene)
  if (!fallback.provider || !fallback.model) {
    return '未配置独立场景模型，将沿用当前默认模型。'
  }

  if (!draftPreferences[scene].provider || !draftPreferences[scene].model) {
    return `当前未单独设置，将回退到 ${fallback.provider} / ${fallback.model}。`
  }

  return `当前保存值：${draftPreferences[scene].provider} / ${draftPreferences[scene].model}`
}

/** 处理 onProviderChange 相关逻辑。 */
function onProviderChange(scene: SceneModelKey, value: string) {
  const provider = (value || '') as ProviderKey | ''
  draftPreferences[scene].provider = provider
  draftPreferences[scene].model = ''
  customModelEnabled[scene] = provider === 'custom'
}

/** 处理 onModelChange 相关逻辑。 */
function onModelChange(scene: SceneModelKey, value: string) {
  if (value === CUSTOM_MODEL_SENTINEL) {
    draftPreferences[scene].model = ''
    customModelEnabled[scene] = true
    return
  }
  draftPreferences[scene].model = value
  customModelEnabled[scene] = draftPreferences[scene].provider === 'custom'
}

/** 处理 loadSceneModels 相关逻辑。 */
async function loadSceneModels() {
  loading.value = true
  try {
    const preferences = await configStore.refreshSceneModelPreferences()
    clonePreferences(preferences)
  } catch (error) {
    toast({
      title: '读取失败',
      description: error instanceof Error ? error.message : '无法读取当前场景模型设置',
      variant: 'destructive',
    })
  } finally {
    loading.value = false
  }
}

/** 处理 fetchModelsForProvider 相关逻辑。 */
async function fetchModelsForProvider(provider: ProviderKey) {
  fetchingModels[provider] = true
  try {
    const result = await fetchAvailableModels(provider)
    if (!result.success) {
      toast({
        title: '获取模型失败',
        description: result.error || '请先在模型管理页确认 API Key 和 Base URL。',
        variant: 'destructive',
      })
      return
    }
    remoteModels[provider] = result.models
    toast({
      title: '模型列表已更新',
      description: `${PROVIDERS.find((item) => item.key === provider)?.name ?? provider} 返回 ${result.models.length} 个模型。`,
    })
  } finally {
    fetchingModels[provider] = false
  }
}

/** 处理 saveAll 相关逻辑。 */
async function saveAll() {
  for (const scene of SCENE_CARDS) {
    const preference = draftPreferences[scene.key]
    if (!!preference.provider !== !!preference.model.trim()) {
      toast({
        title: '配置不完整',
        description: `${scene.label} 需要同时选择 provider 和 model，或保持未单独设置。`,
        variant: 'destructive',
      })
      return
    }
  }

  saving.value = true
  try {
    const nextPreferences: SceneModelPreferences = {
      story_generation: { ...draftPreferences.story_generation },
      input_enhancement: { ...draftPreferences.input_enhancement },
      story_adjustment: { ...draftPreferences.story_adjustment },
    }
    const saved = await configStore.saveSceneModels(nextPreferences)
    clonePreferences(saved)
    toast({ title: '已保存', description: '三个场景的大模型选择已同步到后端。' })
  } catch (error) {
    toast({
      title: '保存失败',
      description: error instanceof Error ? error.message : '无法保存当前场景模型设置',
      variant: 'destructive',
    })
  } finally {
    saving.value = false
  }
}

// 布尔状态 isDirty。
const isDirty = computed(() => JSON.stringify(draftPreferences) !== JSON.stringify(configStore.sceneModelPreferences))

onMounted(async () => {
  if (!configStore.sceneModelsLoading && !configStore.sceneModelPreferences.story_generation.provider && !configStore.sceneModelPreferences.story_generation.model && !configStore.sceneModelPreferences.input_enhancement.provider && !configStore.sceneModelPreferences.input_enhancement.model && !configStore.sceneModelPreferences.story_adjustment.provider && !configStore.sceneModelPreferences.story_adjustment.model) {
    await loadSceneModels()
    return
  }
  clonePreferences(configStore.sceneModelPreferences)
})
</script>

<template>
  <div class="flex-1 overflow-y-auto">
    <div class="mx-auto max-w-5xl space-y-8 px-6 py-8">
      <div class="flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
        <div class="space-y-2">
          <div class="inline-flex items-center gap-2 rounded-full border border-border bg-muted/50 px-3 py-1 text-xs text-muted-foreground">
            <Sparkles class="h-3.5 w-3.5" />
            控制台 / 模型选择
          </div>
          <div>
            <h1 class="text-2xl font-semibold tracking-tight text-foreground">大模型选择</h1>
            <p class="max-w-3xl text-sm leading-6 text-muted-foreground">
              为故事生成、Prompt 优化和故事调整分别指定默认模型。设置保存在后端，页面刷新后仍会保留。
            </p>
          </div>
        </div>

        <div class="flex items-center gap-2">
          <Button variant="outline" class="gap-2" :disabled="loading || saving" @click="loadSceneModels">
            <RefreshCw class="h-4 w-4" :class="{ 'animate-spin': loading }" />
            刷新
          </Button>
          <Button class="gap-2" :disabled="saving || !isDirty" @click="saveAll">
            <Save class="h-4 w-4" />
            {{ saving ? '保存中…' : '保存全部' }}
          </Button>
        </div>
      </div>

      <Separator />

      <div class="grid gap-4 xl:grid-cols-3">
        <section
          v-for="scene in SCENE_CARDS"
          :key="scene.key"
          class="rounded-2xl border border-border bg-card p-5 shadow-sm"
        >
          <div class="flex items-start justify-between gap-3">
            <div class="space-y-2">
              <div class="inline-flex h-10 w-10 items-center justify-center rounded-xl bg-primary/10 text-primary">
                <component :is="scene.icon" class="h-5 w-5" />
              </div>
              <div>
                <h2 class="text-base font-semibold text-foreground">{{ scene.label }}</h2>
                <p class="mt-1 text-sm leading-6 text-muted-foreground">{{ scene.description }}</p>
              </div>
            </div>
            <Badge variant="secondary">后端记录</Badge>
          </div>

          <div class="mt-5 space-y-4">
            <div class="space-y-2">
              <p class="text-xs font-medium uppercase tracking-[0.18em] text-muted-foreground">Provider</p>
              <Select :model-value="draftPreferences[scene.key].provider || '__none__'" @update:model-value="onProviderChange(scene.key, String($event === '__none__' ? '' : $event))">
                <SelectTrigger class="h-10">
                  <SelectValue placeholder="未单独设置" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="__none__">未单独设置</SelectItem>
                  <SelectItem v-for="provider in PROVIDERS" :key="provider.key" :value="provider.key">
                    {{ provider.name }}
                  </SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div v-if="draftPreferences[scene.key].provider" class="space-y-2">
              <div class="flex items-center justify-between gap-3">
                <p class="text-xs font-medium uppercase tracking-[0.18em] text-muted-foreground">Model</p>
                <Button
                  size="sm"
                  variant="outline"
                  class="h-7 px-2 text-xs"
                  :disabled="fetchingModels[draftPreferences[scene.key].provider as ProviderKey]"
                  @click="fetchModelsForProvider(draftPreferences[scene.key].provider as ProviderKey)"
                >
                  {{ fetchingModels[draftPreferences[scene.key].provider as ProviderKey] ? '刷新中…' : '获取模型' }}
                </Button>
              </div>

              <Select
                v-if="!customModelEnabled[scene.key]"
                :model-value="draftPreferences[scene.key].model || '__none__'"
                @update:model-value="onModelChange(scene.key, String($event === '__none__' ? '' : $event))"
              >
                <SelectTrigger class="h-10">
                  <SelectValue placeholder="选择模型" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="__none__">未单独设置</SelectItem>
                  <SelectItem
                    v-for="option in modelOptionsForProvider(draftPreferences[scene.key].provider as ProviderKey)"
                    :key="option.value"
                    :value="option.value"
                  >
                    {{ option.label }}
                  </SelectItem>
                  <SelectItem value="__custom__">手动输入模型名称</SelectItem>
                </SelectContent>
              </Select>

              <Input
                v-if="customModelEnabled[scene.key]"
                v-model="draftPreferences[scene.key].model"
                class="h-10 font-mono text-sm"
                placeholder="输入模型名称，例如 gpt-4.1-mini"
              />

              <div class="rounded-xl border border-dashed border-border bg-muted/30 px-3 py-2 text-xs leading-5 text-muted-foreground">
                {{ effectiveFallbackLabel(scene.key) }}
              </div>
            </div>
            <div
              v-else
              class="rounded-xl border border-dashed border-border bg-muted/30 px-3 py-2 text-xs leading-5 text-muted-foreground"
            >
              {{ effectiveFallbackLabel(scene.key) }}
            </div>
          </div>
        </section>
      </div>
    </div>
  </div>
</template>
