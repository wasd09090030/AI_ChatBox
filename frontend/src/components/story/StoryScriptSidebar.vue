<script setup lang="ts">
// 文件说明：StoryView 严格剧本创作页的“剧本推进侧栏”。
// 页面归属：/story/scripted（仅在严格剧本模式显示）。
// 核心职责：
// - 管理剧本绑定、阶段定位、事件定位与推进意图；
// - 将用户推进操作上抛给 StoryView，由页面统一持久化到后端运行态。
// 非职责边界：不直接发起故事生成，也不直接写入运行态存储。
import { computed } from 'vue'
import { FlagTriangleRight, Milestone, Route, ScrollText, X } from 'lucide-vue-next'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Label } from '@/components/ui/label'
import { ScrollArea } from '@/components/ui/scroll-area'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import type { ScriptDesign, ScriptEventNode, ScriptStage } from '@/domains/story/api/scriptDesignApi'

// 组件输入参数。
// 这些参数由 StoryView 统一计算后传入，确保“推进状态”和“生成状态”来自同一页面真源。
const props = withDefaults(
  defineProps<{
    selectedScriptDesignId: string
    selectedScriptStageId: string
    selectedScriptEventId: string
    progressIntent: 'hold' | 'advance' | 'complete'
    scriptDesigns?: ScriptDesign[]
    scriptStages?: ScriptStage[]
    scriptEvents?: ScriptEventNode[]
    noneOptionValue: string
    progressUpdating?: boolean
    canAdvanceEvent?: boolean
    canAdvanceStage?: boolean
  }>(),
  {
    scriptDesigns: () => [],
    scriptStages: () => [],
    scriptEvents: () => [],
    progressUpdating: false,
    canAdvanceEvent: false,
    canAdvanceStage: false,
  },
)

// 组件事件派发器。
// 约定：本组件仅表达用户意图（选择/推进/保存），不在内部处理业务副作用。
const emit = defineEmits<{
  (event: 'close'): void
  (event: 'update:progressIntent', value: 'hold' | 'advance' | 'complete'): void
  (event: 'update:selectedScriptDesignId', value: string): void
  (event: 'update:selectedScriptStageId', value: string): void
  (event: 'update:selectedScriptEventId', value: string): void
  (event: 'save-progress'): void
  (event: 'advance-event'): void
  (event: 'advance-stage'): void
}>()

// 当前剧本选择代理。
const selectedScriptDesignModel = computed({
  get: () => props.selectedScriptDesignId,
  set: (value: string) => emit('update:selectedScriptDesignId', value),
})

// 当前阶段选择代理。
const selectedScriptStageModel = computed({
  get: () => props.selectedScriptStageId,
  set: (value: string) => emit('update:selectedScriptStageId', value),
})

// 当前事件选择代理。
const selectedScriptEventModel = computed({
  get: () => props.selectedScriptEventId,
  set: (value: string) => emit('update:selectedScriptEventId', value),
})

// 推进意图选择代理（仅描写 / 推进事件 / 完成事件）。
const progressIntentModel = computed({
  get: () => props.progressIntent,
  set: (value: 'hold' | 'advance' | 'complete') => emit('update:progressIntent', value),
})

// 推进意图角标文案。
// 作用：在侧栏顶部快速提示当前轮次的推进语义，减少误操作。
const progressIntentLabel = computed(() => {
  if (props.progressIntent === 'complete') return '完成事件'
  if (props.progressIntent === 'advance') return '推进事件'
  return '仅描写'
})

// 是否已绑定剧本。
// 作用：控制阶段/事件与推进按钮可用性，避免在无主线上下文下推进。
const hasBoundScript = computed(() => props.selectedScriptDesignId !== props.noneOptionValue)
</script>

<template>
  <aside class="w-80 border-l border-border bg-background flex flex-col shrink-0">
    <div class="flex items-start justify-between gap-3 border-b border-border px-4 py-4">
      <div class="min-w-0">
        <p class="flex items-center gap-1.5 text-sm font-semibold text-foreground">
          <Route class="h-4 w-4 text-orange-600" />
          严格剧本推进
        </p>
        <p class="mt-1 text-xs leading-5 text-muted-foreground">
          这里控制主线绑定、阶段定位和事件定位。输入框只负责本轮微调，不负责主线调度。
        </p>
      </div>
      <Button size="icon" variant="ghost" class="h-8 w-8 shrink-0" @click="emit('close')">
        <X class="h-4 w-4" />
      </Button>
    </div>

    <ScrollArea class="flex-1">
      <div class="space-y-4 px-4 py-4">
        <section class="rounded-xl border border-orange-200/80 bg-orange-50/70 p-4">
          <div class="flex items-center justify-between gap-2">
            <p class="text-sm font-semibold text-orange-950">结构主导</p>
            <Badge variant="outline" class="border-orange-200 bg-white text-[10px] text-orange-700">
              {{ progressIntentLabel }}
            </Badge>
          </div>
          <p class="mt-2 text-xs leading-5 text-orange-900/80">
            当前阶段和事件是严格模式的真实推进单元。Prompt 不会直接把主线跳到别的节点。
          </p>
          <div class="mt-3 space-y-2">
            <Label class="text-xs text-orange-800/80">推进意图</Label>
            <Select v-model="progressIntentModel" :disabled="progressUpdating">
              <SelectTrigger class="h-9 border-orange-200 bg-white text-xs">
                <SelectValue placeholder="选择推进意图" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="hold">仅描写</SelectItem>
                <SelectItem value="advance">推进事件</SelectItem>
                <SelectItem value="complete">完成事件</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </section>

        <section class="space-y-3 rounded-xl border border-border/70 bg-card p-4">
          <div class="flex items-center gap-2">
            <ScrollText class="h-4 w-4 text-orange-600" />
            <p class="text-sm font-semibold text-foreground">剧本绑定</p>
          </div>

          <div class="space-y-2">
            <Label class="text-xs text-muted-foreground">当前剧本</Label>
            <Select v-model="selectedScriptDesignModel" :disabled="progressUpdating">
              <SelectTrigger class="h-9 text-xs">
                <SelectValue placeholder="选择剧本设计" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem :value="noneOptionValue">不指定剧本设计</SelectItem>
                <SelectItem
                  v-for="design in scriptDesigns"
                  :key="design.id"
                  :value="design.id"
                >
                  {{ design.title }}
                </SelectItem>
              </SelectContent>
            </Select>
          </div>

          <p class="text-[11px] leading-5 text-muted-foreground">
            <template v-if="hasBoundScript">
              绑定后，后端会以 runtime state 和当前事件作为主线推进依据。
            </template>
            <template v-else>
              还未绑定剧本。严格模式建议先绑定剧本，再执行阶段和事件控制。
            </template>
          </p>
        </section>

        <section class="space-y-3 rounded-xl border border-border/70 bg-card p-4">
          <div class="flex items-center gap-2">
            <Milestone class="h-4 w-4 text-orange-600" />
            <p class="text-sm font-semibold text-foreground">阶段控制</p>
          </div>

          <div class="space-y-2">
            <Label class="text-xs text-muted-foreground">当前阶段</Label>
            <Select v-model="selectedScriptStageModel" :disabled="progressUpdating || !hasBoundScript">
              <SelectTrigger class="h-9 text-xs">
                <SelectValue placeholder="选择阶段" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem :value="noneOptionValue">自动选择阶段</SelectItem>
                <SelectItem
                  v-for="stage in scriptStages"
                  :key="stage.id"
                  :value="stage.id"
                >
                  {{ stage.title }}
                </SelectItem>
              </SelectContent>
            </Select>
          </div>

          <Button
            size="sm"
            variant="outline"
            class="h-8 w-full text-xs"
            :disabled="progressUpdating || !canAdvanceStage"
            @click="emit('advance-stage')"
          >
            推进到下一阶段
          </Button>
        </section>

        <section class="space-y-3 rounded-xl border border-border/70 bg-card p-4">
          <div class="flex items-center gap-2">
            <FlagTriangleRight class="h-4 w-4 text-orange-600" />
            <p class="text-sm font-semibold text-foreground">事件控制</p>
          </div>

          <div class="space-y-2">
            <Label class="text-xs text-muted-foreground">当前事件</Label>
            <Select v-model="selectedScriptEventModel" :disabled="progressUpdating || !hasBoundScript">
              <SelectTrigger class="h-9 text-xs">
                <SelectValue placeholder="选择事件" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem :value="noneOptionValue">自动选择事件</SelectItem>
                <SelectItem
                  v-for="eventNode in scriptEvents"
                  :key="eventNode.id"
                  :value="eventNode.id"
                >
                  {{ eventNode.title }}
                </SelectItem>
              </SelectContent>
            </Select>
          </div>

          <div class="grid grid-cols-1 gap-2">
            <Button
              size="sm"
              class="h-8 text-xs"
              :disabled="progressUpdating || !hasBoundScript"
              @click="emit('save-progress')"
            >
              保存当前推进
            </Button>
            <Button
              size="sm"
              variant="outline"
              class="h-8 text-xs"
              :disabled="progressUpdating || !canAdvanceEvent"
              @click="emit('advance-event')"
            >
              推进到下一事件
            </Button>
          </div>
        </section>
      </div>
    </ScrollArea>
  </aside>
</template>
