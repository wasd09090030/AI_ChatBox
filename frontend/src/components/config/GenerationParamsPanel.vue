<script setup lang="ts">
// 文件说明：前端可复用界面组件。
import { Badge } from '@/components/ui/badge'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip'
import { Info } from 'lucide-vue-next'
import type { ToneInfo } from '@/components/config/types'

// 变量作用：变量 props，用于 props 相关配置或状态。
const props = defineProps<{
  temperature: number
  maxTokens: number
  tempInput: string
  tempError: string
  maxTokensInput: string
  maxTokensError: string
  currentToneInfo: ToneInfo | null
  currentWorldName?: string
  effectiveTemp: number
}>()

// 变量作用：变量 emit，用于 emit 相关配置或状态。
const emit = defineEmits<{
  (event: 'temp-input', payload: Event): void
  (event: 'max-tokens-input', payload: Event): void
}>()

/** 功能：函数 handleTempInput，负责 handleTempInput 相关处理。 */
function handleTempInput(event: Event) {
  emit('temp-input', event)
}

/** 功能：函数 handleMaxTokensInput，负责 handleMaxTokensInput 相关处理。 */
function handleMaxTokensInput(event: Event) {
  emit('max-tokens-input', event)
}
</script>

<template>
  <section class="space-y-4">
    <div>
      <h2 class="text-base font-medium">生成参数</h2>
      <p class="text-sm text-muted-foreground mt-0.5">影响 AI 输出的创意程度和长度</p>
    </div>

    <div class="grid grid-cols-2 gap-6">
      <div class="space-y-2">
        <Label for="temperature">
          Temperature
          <span class="text-muted-foreground font-normal ml-1">({{ temperature }})</span>
        </Label>
        <Input
          id="temperature"
          :value="tempInput"
          type="number"
          min="0"
          max="2"
          step="0.1"
          :class="{ 'border-destructive': tempError }"
          @input="handleTempInput"
        />
        <p v-if="tempError" class="text-xs text-destructive">{{ tempError }}</p>
        <p v-else class="text-xs text-muted-foreground">越高越有创意，越低越精确（0 ~ 2）</p>

        <div class="rounded-md border border-border/60 bg-muted/30 p-3 space-y-2 mt-1">
          <div class="flex items-center gap-1.5 text-xs font-medium text-muted-foreground">
            <Info class="h-3.5 w-3.5" />
            自适应温度
            <TooltipProvider>
              <Tooltip>
                <TooltipTrigger as-child>
                  <span class="text-[10px] underline underline-offset-2 cursor-help">查看偏移表</span>
                </TooltipTrigger>
                <TooltipContent side="right" class="max-w-xs">
                  <div class="text-xs space-y-1">
                    <p class="font-medium mb-1">叙事基调 → 温度偏移</p>
                    <div class="grid grid-cols-2 gap-x-4 gap-y-0.5">
                      <span>黑暗/严肃/紧张</span><span class="text-right font-mono">-0.15</span>
                      <span>恐怖</span><span class="text-right font-mono">-0.10</span>
                      <span>悬疑</span><span class="text-right font-mono">-0.05</span>
                      <span>史诗/亲密</span><span class="text-right font-mono">+0.05</span>
                      <span>浪漫/幽默/喜剧</span><span class="text-right font-mono">+0.10</span>
                    </div>
                  </div>
                </TooltipContent>
              </Tooltip>
            </TooltipProvider>
          </div>

          <div v-if="currentToneInfo && currentToneInfo.matched" class="flex items-center gap-2 text-xs">
            <Badge variant="secondary" class="text-[11px] gap-1">
              {{ currentWorldName }}
            </Badge>
            <span class="text-muted-foreground">基调</span>
            <Badge variant="outline" class="text-[11px]">{{ currentToneInfo.label }}</Badge>
            <span class="font-mono text-muted-foreground">
              {{ temperature }} {{ currentToneInfo.offset >= 0 ? '+' : '' }}{{ currentToneInfo.offset }}
              = <span class="font-semibold text-foreground">{{ effectiveTemp.toFixed(2) }}</span>
            </span>
          </div>
          <div v-else-if="currentToneInfo && !currentToneInfo.matched" class="text-xs text-muted-foreground">
            当前世界基调「{{ currentToneInfo.tone }}」暂无偏移，生效温度 = {{ temperature }}
          </div>
          <div v-else class="text-xs text-muted-foreground">
            未选择世界，生成时将根据世界叙事基调自动微调温度
          </div>
        </div>
      </div>

      <div class="space-y-2">
        <Label for="max-tokens">
          Max Tokens
          <span class="text-muted-foreground font-normal ml-1">({{ maxTokens }})</span>
        </Label>
        <Input
          id="max-tokens"
          :value="maxTokensInput"
          type="number"
          min="100"
          max="32000"
          step="100"
          :class="{ 'border-destructive': maxTokensError }"
          @input="handleMaxTokensInput"
        />
        <p v-if="maxTokensError" class="text-xs text-destructive">{{ maxTokensError }}</p>
        <p v-else class="text-xs text-muted-foreground">单次生成最大 token 数（100 ~ 32000）</p>
      </div>
    </div>
  </section>
</template>
