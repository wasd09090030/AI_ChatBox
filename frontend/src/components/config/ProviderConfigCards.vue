<script setup lang="ts">
import { Eye, EyeOff, Check, ChevronDown, ChevronRight, Link, Wifi, Loader2, List, Star } from 'lucide-vue-next'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Badge } from '@/components/ui/badge'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from '@/components/ui/alert-dialog'
import type { TestConnectionResult, ModelInfo } from '@/domains/settings/api/providerConfigApi'
import type { ProviderKey } from '@/utils/types'
import type { ProviderMeta, ProviderModelOption } from '@/components/config/types'

const props = defineProps<{
  providers: ProviderMeta[]
  keyInputs: Record<ProviderKey, string>
  baseUrlInputs: Record<ProviderKey, string>
  showKey: Record<ProviderKey, boolean>
  showAdvanced: Record<ProviderKey, boolean>
  saving: Record<ProviderKey, boolean>
  testing: Record<ProviderKey, boolean>
  testResults: Record<ProviderKey, TestConnectionResult | null>
  fetchingModels: Record<ProviderKey, boolean>
  remoteModels: Record<ProviderKey, ModelInfo[]>
  selectedModels: Record<ProviderKey, string>
  isDefaultProvider?: ProviderKey | null
  keyStatus: (provider: ProviderKey) => string | undefined
  modelsForProvider: (provider: ProviderKey) => ProviderModelOption[]
  persistSelectedModels: () => void
  saveKey: (provider: ProviderKey) => void | Promise<void>
  deleteKey: (provider: ProviderKey) => void | Promise<void>
  testConnection: (provider: ProviderKey) => void | Promise<void>
  fetchModels: (provider: ProviderKey) => void | Promise<void>
  setAsDefault: (provider: ProviderKey) => void | Promise<void>
  toggleAdvanced: (provider: ProviderKey) => void
  saveBaseUrl: (provider: ProviderKey) => void | Promise<void>
}>()

function toggleKeyVisibility(provider: ProviderKey) {
  props.showKey[provider] = !props.showKey[provider]
}

function onSelectModel(provider: ProviderKey, value: unknown) {
  if (value === null || value === undefined || value === '') return
  props.selectedModels[provider] = String(value)
  props.persistSelectedModels()
}
</script>

<template>
  <section class="space-y-4">
    <div>
      <h2 class="text-base font-medium">AI 提供商</h2>
      <p class="text-sm text-muted-foreground mt-0.5">
        配置各提供商的 API Key，支持自定义 Base URL（用于国内代理或自部署）
      </p>
    </div>

    <div class="space-y-3">
      <div
        v-for="p in providers"
        :key="p.key"
        class="rounded-lg border border-border bg-card overflow-hidden"
      >
        <div class="flex items-center gap-3 p-4">
          <div :class="`${p.color} w-2 h-2 rounded-full shrink-0`" />
          <span class="font-medium text-sm flex-1">{{ p.name }}</span>

          <Badge
            v-if="isDefaultProvider === p.key && keyStatus(p.key)"
            variant="default"
            class="text-xs gap-1 bg-primary/90"
          >
            <Star class="h-2.5 w-2.5" />
            默认
          </Badge>

          <Badge :variant="keyStatus(p.key) ? 'default' : 'secondary'" class="text-xs">
            {{ keyStatus(p.key) ? '已配置' : '未配置' }}
          </Badge>
          <Badge v-if="keyStatus(p.key)" variant="outline" class="text-xs font-mono">
            {{ keyStatus(p.key) }}
          </Badge>

          <AlertDialog v-if="keyStatus(p.key)">
            <AlertDialogTrigger as-child>
              <Button size="sm" variant="ghost" class="text-destructive hover:text-destructive h-7 px-2 text-xs">
                删除
              </Button>
            </AlertDialogTrigger>
            <AlertDialogContent>
              <AlertDialogHeader>
                <AlertDialogTitle>删除 API Key</AlertDialogTitle>
                <AlertDialogDescription>
                  确定要删除 {{ p.name }} API Key？
                </AlertDialogDescription>
              </AlertDialogHeader>
              <AlertDialogFooter>
                <AlertDialogCancel>取消</AlertDialogCancel>
                <AlertDialogAction variant="destructive" @click="deleteKey(p.key)">删除</AlertDialogAction>
              </AlertDialogFooter>
            </AlertDialogContent>
          </AlertDialog>
        </div>

        <div class="px-4 pb-3 space-y-2 border-t border-border/50 pt-3 bg-muted/20">
          <div class="flex gap-2">
            <div class="relative flex-1">
              <Input
                v-model="keyInputs[p.key]"
                :type="showKey[p.key] ? 'text' : 'password'"
                :placeholder="keyStatus(p.key) ? '输入新 Key 以替换…' : p.placeholder"
                class="pr-10 font-mono text-sm h-8"
                @keydown.enter="saveKey(p.key)"
              />
              <Button
                size="icon"
                variant="ghost"
                class="absolute right-1 top-1/2 -translate-y-1/2 h-6 w-6"
                @click="toggleKeyVisibility(p.key)"
              >
                <Eye v-if="!showKey[p.key]" class="h-3 w-3" />
                <EyeOff v-else class="h-3 w-3" />
              </Button>
            </div>
            <Button
              size="sm"
              class="h-8"
              :disabled="!keyInputs[p.key].trim() || saving[p.key]"
              @click="saveKey(p.key)"
            >
              <Check class="h-3.5 w-3.5 mr-1" />
              {{ saving[p.key] ? '保存中…' : '保存' }}
            </Button>
            <Button
              size="sm"
              variant="outline"
              class="h-8 gap-1"
              :disabled="testing[p.key] || !keyStatus(p.key)"
              @click="testConnection(p.key)"
            >
              <Loader2 v-if="testing[p.key]" class="h-3.5 w-3.5 animate-spin" />
              <Wifi v-else class="h-3.5 w-3.5" />
              测试
            </Button>
          </div>

          <div
            v-if="testResults[p.key]"
            :class="[
              'text-xs px-2 py-1 rounded flex items-center gap-1.5',
              testResults[p.key]!.success
                ? 'bg-green-500/10 text-green-600 dark:text-green-400'
                : 'bg-destructive/10 text-destructive'
            ]"
          >
            <Check v-if="testResults[p.key]!.success" class="h-3 w-3 shrink-0" />
            <span class="leading-tight">{{ testResults[p.key]!.message }}</span>
          </div>

          <div v-if="keyStatus(p.key)" class="flex items-center gap-2 pt-1">
            <Select :model-value="selectedModels[p.key]" @update:model-value="(v) => onSelectModel(p.key, v)">
              <SelectTrigger class="h-8 flex-1 text-xs">
                <SelectValue :placeholder="modelsForProvider(p.key).length ? '选择模型…' : '请先查询模型'" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem
                  v-for="m in modelsForProvider(p.key)"
                  :key="m.value"
                  :value="m.value"
                >
                  {{ m.label }}
                </SelectItem>
                <template v-if="p.key === 'custom' || !modelsForProvider(p.key).length">
                  <SelectItem value="__custom__">手动输入模型名称</SelectItem>
                </template>
              </SelectContent>
            </Select>

            <Input
              v-if="p.key === 'custom' || selectedModels[p.key] === '__custom__'"
              v-model="selectedModels[p.key]"
              placeholder="例如：llama-3.1-8b"
              class="h-8 text-xs font-mono flex-1"
            />

            <Button
              size="sm"
              variant="outline"
              class="h-8 gap-1 shrink-0"
              :disabled="fetchingModels[p.key]"
              @click="fetchModels(p.key)"
            >
              <Loader2 v-if="fetchingModels[p.key]" class="h-3.5 w-3.5 animate-spin" />
              <List v-else class="h-3.5 w-3.5" />
              {{ remoteModels[p.key].length ? `${remoteModels[p.key].length}` : '获取' }}
            </Button>

            <Button
              size="sm"
              :variant="isDefaultProvider === p.key ? 'default' : 'outline'"
              class="h-8 gap-1 shrink-0"
              :disabled="!selectedModels[p.key] || selectedModels[p.key] === '__custom__'"
              @click="setAsDefault(p.key)"
            >
              <Star class="h-3.5 w-3.5" />
              {{ isDefaultProvider === p.key ? '已默认' : '设为默认' }}
            </Button>
          </div>

          <div class="flex items-center justify-between">
            <p v-if="p.docsUrl" class="text-xs text-muted-foreground">
              <a :href="p.docsUrl" target="_blank" class="underline underline-offset-2 hover:text-foreground inline-flex items-center gap-1">
                <Link class="h-3 w-3" />
                获取 API Key
              </a>
            </p>
            <p v-else class="text-xs text-muted-foreground">需要配置 Base URL</p>

            <Button
              size="sm"
              variant="ghost"
              class="h-6 px-2 text-xs text-muted-foreground gap-1"
              @click="toggleAdvanced(p.key)"
            >
              <ChevronDown v-if="showAdvanced[p.key]" class="h-3 w-3" />
              <ChevronRight v-else class="h-3 w-3" />
              自定义 Base URL
            </Button>
          </div>

          <div v-show="showAdvanced[p.key]" class="space-y-1.5 pt-1">
            <Label class="text-xs text-muted-foreground">
              Base URL
              <span class="font-normal ml-1 text-muted-foreground/70">
                （留空使用默认：{{ p.defaultBaseUrl || '请填写' }}）
              </span>
            </Label>
            <div class="flex gap-2">
              <Input
                v-model="baseUrlInputs[p.key]"
                :placeholder="p.defaultBaseUrl || 'https://your-proxy.example.com/v1'"
                class="font-mono text-xs h-8"
              />
              <Button size="sm" class="h-8" @click="saveBaseUrl(p.key)">
                <Check class="h-3.5 w-3.5" />
              </Button>
            </div>
          </div>
        </div>
      </div>
    </div>
  </section>
</template>
