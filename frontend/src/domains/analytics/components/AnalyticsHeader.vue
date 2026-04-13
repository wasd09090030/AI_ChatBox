<script setup lang="ts">
// 文件说明：前端业务域逻辑与接口封装。
import { BarChart2, RefreshCw } from 'lucide-vue-next'
import { Button } from '@/components/ui/button'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import type { AnalyticsFilterOption } from '@/domains/analytics/types'

// 组件输入参数。
const props = defineProps<{
  days: string
  refreshing?: boolean
  selectedModel: string
  selectedWorldId: string
  selectedEventType: string
  modelOptions: AnalyticsFilterOption[]
  worldOptions: Array<AnalyticsFilterOption & { label: string }>
  eventTypeOptions: AnalyticsFilterOption[]
  eyebrow?: string
  title?: string
  description?: string
}>()

// 组件事件派发器。
const emit = defineEmits<{
  (event: 'update:days', value: string): void
  (event: 'update:model', value: string): void
  (event: 'update:world-id', value: string): void
  (event: 'update:event-type', value: string): void
  (event: 'refresh'): void
}>()
</script>

<template>
  <header class="sticky top-0 z-10 border-b border-border bg-background/85 backdrop-blur">
    <div class="flex flex-col gap-4 px-6 py-5 md:flex-row md:items-end md:justify-between">
      <div class="space-y-2">
        <div class="inline-flex items-center gap-2 rounded-full border border-border bg-muted/50 px-3 py-1 text-xs text-muted-foreground">
          <BarChart2 class="h-3.5 w-3.5" />
          {{ props.eyebrow || '创作数据面板' }}
        </div>
        <div>
          <h1 class="text-2xl font-semibold tracking-tight text-foreground">{{ props.title || '数据统计' }}</h1>
          <p class="max-w-2xl text-sm leading-6 text-muted-foreground">
            {{ props.description || '把请求、模型、世界设定、上下文命中和 token 消耗拆开看，才能知道故事为什么变长、变慢，或者开始跑偏。' }}
          </p>
        </div>
      </div>

      <div class="flex flex-wrap items-center gap-3 self-start md:justify-end">
        <Select :model-value="props.days" @update:model-value="emit('update:days', String($event))">
          <SelectTrigger class="h-9 w-28 text-xs">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="7">近 7 天</SelectItem>
            <SelectItem value="14">近 14 天</SelectItem>
            <SelectItem value="30">近 30 天</SelectItem>
            <SelectItem value="60">近 60 天</SelectItem>
          </SelectContent>
        </Select>

        <Select :model-value="props.selectedModel" @update:model-value="emit('update:model', String($event))">
          <SelectTrigger class="h-9 w-44 text-xs">
            <SelectValue placeholder="全部模型" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">全部模型</SelectItem>
            <SelectItem v-for="option in props.modelOptions" :key="option.value" :value="option.value">
              {{ option.value }} ({{ option.count }})
            </SelectItem>
          </SelectContent>
        </Select>

        <Select :model-value="props.selectedWorldId" @update:model-value="emit('update:world-id', String($event))">
          <SelectTrigger class="h-9 w-44 text-xs">
            <SelectValue placeholder="全部世界" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">全部世界</SelectItem>
            <SelectItem v-for="option in props.worldOptions" :key="option.value" :value="option.value">
              {{ option.label }} ({{ option.count }})
            </SelectItem>
          </SelectContent>
        </Select>

        <Select :model-value="props.selectedEventType" @update:model-value="emit('update:event-type', String($event))">
          <SelectTrigger class="h-9 w-44 text-xs">
            <SelectValue placeholder="全部类型" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">全部类型</SelectItem>
            <SelectItem v-for="option in props.eventTypeOptions" :key="option.value" :value="option.value">
              {{ option.value }} ({{ option.count }})
            </SelectItem>
          </SelectContent>
        </Select>

        <Button variant="outline" class="h-9 gap-2" :disabled="props.refreshing" @click="emit('refresh')">
          <RefreshCw class="h-3.5 w-3.5" :class="{ 'animate-spin': props.refreshing }" />
          刷新
        </Button>
      </div>
    </div>
  </header>
</template>
