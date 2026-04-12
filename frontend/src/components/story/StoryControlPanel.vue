<script setup lang="ts">
// 文件说明：前端可复用界面组件。
import { computed } from 'vue'
import { ChevronDown, PenLine } from 'lucide-vue-next'
import { Badge } from '@/components/ui/badge'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { cn } from '@/lib/utils'
import type { StoryMode } from '@/components/story/types'

// 变量作用：变量 props，用于 props 相关配置或状态。
const props = defineProps<{
  show: boolean
  collapsible?: boolean
  storyMode: StoryMode
  authorsNote: string
  instruction: string
  controlBadgeText: string
  modeLabels: Record<StoryMode, string>
}>()

// 变量作用：变量 emit，用于 emit 相关配置或状态。
const emit = defineEmits<{
  (event: 'update:show', value: boolean): void
  (event: 'update:storyMode', value: StoryMode): void
  (event: 'update:authorsNote', value: string): void
  (event: 'update:instruction', value: string): void
}>()

const modeOptions: StoryMode[] = ['narrative', 'choices', 'instruction']

// 变量作用：变量 showModel，用于 showModel 相关配置或状态。
const showModel = computed({
  get: () => props.show,
  set: (value: boolean) => emit('update:show', value),
})

// 变量作用：变量 storyModeModel，用于 storyModeModel 相关配置或状态。
const storyModeModel = computed({
  get: () => props.storyMode,
  set: (value: StoryMode) => emit('update:storyMode', value),
})

// 变量作用：变量 instructionModel，用于 instructionModel 相关配置或状态。
const instructionModel = computed({
  get: () => props.instruction,
  set: (value: string) => emit('update:instruction', value),
})

// 变量作用：变量 authorsNoteModel，用于 authorsNoteModel 相关配置或状态。
const authorsNoteModel = computed({
  get: () => props.authorsNote,
  set: (value: string) => emit('update:authorsNote', value),
})

/** 功能：函数 selectMode，负责 selectMode 相关处理。 */
function selectMode(mode: StoryMode) {
  storyModeModel.value = mode
}
</script>

<template>
  <div :class="props.collapsible === false ? 'space-y-3' : 'border-t border-border'">
    <button
      v-if="props.collapsible !== false"
      class="w-full flex items-center justify-between px-4 py-2.5 text-xs text-muted-foreground hover:bg-muted/30 transition-colors"
      @click="showModel = !showModel"
    >
      <span class="flex items-center gap-1.5">
        <PenLine class="h-3.5 w-3.5" />
        <span class="font-medium">创作控制</span>
        <Badge v-if="controlBadgeText" variant="secondary" class="text-[10px] font-normal">
          {{ controlBadgeText }}
        </Badge>
      </span>
      <ChevronDown
        :class="cn('h-3.5 w-3.5 transition-transform duration-200', showModel && 'rotate-180')"
      />
    </button>

    <div v-show="props.collapsible === false || showModel" :class="props.collapsible === false ? 'space-y-3' : 'px-4 pb-4 pt-1 bg-muted/10 space-y-3'">
      <div class="flex items-center gap-2">
        <span class="text-xs text-muted-foreground w-8 shrink-0">模式</span>
        <div class="flex gap-1">
          <button
            v-for="m in modeOptions"
            :key="m"
            :class="cn(
              'h-6 px-3 text-xs rounded-md border transition-colors',
              storyModeModel === m
                ? 'bg-primary text-primary-foreground border-primary'
                : 'border-border text-muted-foreground hover:bg-muted/60 hover:text-foreground',
            )"
            @click="selectMode(m)"
          >
            {{ modeLabels[m] }}
          </button>
        </div>
        <span class="text-[11px] text-muted-foreground">
          <template v-if="storyModeModel === 'choices'">AI 给出 3 个分支</template>
          <template v-else-if="storyModeModel === 'instruction'">强制推进情节</template>
          <template v-else>自由叙事</template>
        </span>
      </div>

      <div v-if="storyModeModel === 'instruction'" class="flex items-center gap-2">
        <span class="text-xs text-muted-foreground w-8 shrink-0">指令</span>
        <Input
          v-model="instructionModel"
          placeholder="例：引入神秘刺客，进入战斗场景"
          class="h-7 text-xs flex-1"
        />
      </div>

      <div class="flex items-start gap-2">
        <span class="text-xs text-muted-foreground w-8 shrink-0 pt-1.5">旁白</span>
        <div class="flex-1 space-y-1">
          <Textarea
            v-model="authorsNoteModel"
            placeholder="向 AI 注入叙事提示，例：保持神秘气氛，降低战斗烈度"
            class="min-h-[52px] max-h-[96px] text-xs resize-none"
          />
          <p class="text-[10px] text-muted-foreground">每轮生成都将携带此 Author's Note</p>
        </div>
      </div>
    </div>
  </div>
</template>
