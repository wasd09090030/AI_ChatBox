<script setup lang="ts">
// 文件说明：StoryView 主内容区的会话列表。
// 页面归属：/story/improv 与 /story/scripted 共用。
// 核心职责：
// - 渲染“用户输入 -> AI 输出”段落链；
// - 在最后一段提供撤销/重生成；
// - 承接分支卡片的分支续写事件。
import { Bot, BookOpen, Sparkles, RefreshCw, RotateCcw } from 'lucide-vue-next'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import BranchChoiceCard from '@/components/story/BranchChoiceCard.vue'
import type { StoredStory, StorySegment } from '@/components/story/types'

// 组件输入参数。
// 其中 currentStory 由 StoryView 维护，formatTime 由页面注入统一格式化策略。
const props = defineProps<{
  currentStory: StoredStory | null
  generating: boolean
  formatTime: (timestamp: string) => string
}>()

// 组件事件派发器：把段落级交互上抛给 StoryView 统一处理。
const emit = defineEmits<{
  (event: 'branch-send', payload: { prompt: string; chosenIdx: number }): void
  (event: 'rollback-last'): void
  (event: 'regenerate-last'): void
}>()

/** 判断给定段落是否为最后一段。最后一段才允许撤销/重生成。 */
function isLastSeg(seg: StorySegment) {
  const segments = props.currentStory?.segments ?? []
  return segments[segments.length - 1]?.id === seg.id
}

/** 转发分支续写请求（选择分支后继续生成）。 */
function handleBranchSend(payload: { prompt: string; chosenIdx: number }) {
  emit('branch-send', payload)
}

/** 生成段落来源标签，帮助用户区分该段是在哪种创作模式下产生。 */
function getSegmentModeLabel(seg: StorySegment) {
  if (seg.creation_mode === 'scripted') return '严格剧本输入'
  if (seg.creation_mode === 'improv') return '渐进式输入'
  return '历史输入'
}
</script>

<template>
  <div v-if="!currentStory" class="h-full flex flex-col items-center justify-center text-center py-20 text-muted-foreground">
    <BookOpen class="h-14 w-14 mb-4 opacity-20" />
    <p class="text-base font-medium">选择或创建一个故事</p>
    <p class="text-sm mt-1 opacity-70">从左侧世界选择开始</p>
  </div>

  <template v-else>
    <div v-if="!currentStory.segments.length" class="flex flex-col items-center justify-center py-20 text-muted-foreground">
      <Sparkles class="h-10 w-10 mb-3 opacity-20" />
      <p class="text-sm">输入提示词，开始你的故事</p>
    </div>

    <div v-for="seg in currentStory.segments" :key="seg.id" class="max-w-3xl mx-auto w-full">
      <div class="flex gap-3 mb-3 justify-end">
        <div class="max-w-lg">
          <div class="mb-1 flex justify-end">
            <Badge
              variant="outline"
              class="border-border/70 bg-background/80 text-[10px] text-muted-foreground"
            >
              {{ getSegmentModeLabel(seg) }}
            </Badge>
          </div>
          <div class="bg-primary text-primary-foreground rounded-xl px-4 py-2.5 text-sm leading-relaxed">
            {{ seg.prompt }}
          </div>
          <p class="text-[11px] text-muted-foreground mt-1 text-right">{{ formatTime(seg.timestamp) }}</p>
        </div>
      </div>

      <div class="flex gap-3">
        <div class="h-7 w-7 rounded-full bg-muted flex items-center justify-center shrink-0 mt-0.5">
          <Bot class="h-4 w-4 text-muted-foreground" />
        </div>
        <div class="flex-1 min-w-0">
          <div v-if="!seg.content" class="flex gap-1 items-center py-3">
            <span class="h-2 w-2 rounded-full bg-muted-foreground/40 animate-bounce [animation-delay:0ms]" />
            <span class="h-2 w-2 rounded-full bg-muted-foreground/40 animate-bounce [animation-delay:150ms]" />
            <span class="h-2 w-2 rounded-full bg-muted-foreground/40 animate-bounce [animation-delay:300ms]" />
          </div>
          <div v-else class="prose prose-sm max-w-none text-foreground bg-muted/40 rounded-xl px-4 py-3 leading-relaxed whitespace-pre-wrap">
            {{ seg.content }}
          </div>

          <BranchChoiceCard
            v-if="seg.choices?.length && (!generating || isLastSeg(seg))"
            :seg-id="seg.id"
            :choices="seg.choices"
            :generating="generating"
            @send="handleBranchSend"
          />

          <div class="mt-1.5 flex items-center gap-1">
            <div v-if="seg.retrieved_context?.length" class="flex-1 flex flex-wrap gap-1">
              <Badge
                v-for="(_, i) in seg.retrieved_context.slice(0, 3)"
                :key="i"
                variant="outline"
                class="text-[10px] text-muted-foreground"
              >
                设定 {{ i + 1 }}
              </Badge>
            </div>
            <div v-else class="flex-1" />
            <template v-if="isLastSeg(seg) && !generating && seg.content">
              <Button
                size="sm"
                variant="ghost"
                class="h-6 px-2 text-[11px] text-muted-foreground hover:text-foreground gap-1"
                @click="emit('rollback-last')"
              >
                <RotateCcw class="h-3 w-3" />
                撤销
              </Button>
              <Button
                size="sm"
                variant="ghost"
                class="h-6 px-2 text-[11px] text-muted-foreground hover:text-foreground gap-1"
                @click="emit('regenerate-last')"
              >
                <RefreshCw class="h-3 w-3" />
                重新生成
              </Button>
            </template>
          </div>
        </div>
      </div>
    </div>
  </template>
</template>
