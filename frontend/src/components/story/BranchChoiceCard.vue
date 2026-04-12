<script setup lang="ts">
/**
 * BranchChoiceCard
 *
 * Renders story choices with a "select → supplement → send" state machine.
 * Completely decoupled from the global userInput textarea.
 *
 * State machine per card:
 *   idle ──(click)──▶ selected ──(optional type)──▶ supplemented
 *   selected ──(click ✕)──▶ idle
 *   selected|supplemented ──(send)──▶ emits 'send'
 */
import { ref, computed } from 'vue'
import { Send, X, GitBranch } from 'lucide-vue-next'
import { Textarea } from '@/components/ui/textarea'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { cn } from '@/lib/utils'

// 变量作用：变量 props，用于 props 相关配置或状态。
const props = defineProps<{
  segId: string
  choices: string[]
  generating: boolean
}>()

// 变量作用：变量 emit，用于 emit 相关配置或状态。
const emit = defineEmits<{
  (e: 'send', payload: { prompt: string; chosenIdx: number }): void
}>()

// ── Internal state ───────────────────────────────────────────────────────────
const selectedIdx = ref<number | null>(null)
// 变量作用：变量 supplement，用于 supplement 相关配置或状态。
const supplement = ref('')
// 变量作用：变量 supplementRef，用于 supplementRef 相关配置或状态。
const supplementRef = ref<HTMLTextAreaElement | null>(null)

// ── Computed ─────────────────────────────────────────────────────────────────
const isSelected = (idx: number) => selectedIdx.value === idx

// 变量作用：变量 finalPrompt，用于 finalPrompt 相关配置或状态。
const finalPrompt = computed(() => {
  if (selectedIdx.value === null) return ''
  const base = props.choices[selectedIdx.value]!
  const sup = supplement.value.trim()
  return sup ? `${base}\n\n${sup}` : base
})

// ── Handlers ──────────────────────────────────────────────────────────────────
function selectCard(idx: number) {
  if (props.generating) return
  if (selectedIdx.value === idx) {
    // clicking again deselects
    selectedIdx.value = null
    supplement.value = ''
    return
  }
  selectedIdx.value = idx
  supplement.value = ''
  // focus supplement textarea after DOM update
  setTimeout(() => supplementRef.value?.focus(), 50)
}

/** 功能：函数 cancelSelection，负责 cancelSelection 相关处理。 */
function cancelSelection() {
  selectedIdx.value = null
  supplement.value = ''
}

/** 功能：函数 sendBranch，负责 sendBranch 相关处理。 */
function sendBranch() {
  if (selectedIdx.value === null || props.generating) return
  emit('send', {
    prompt: finalPrompt.value,
    chosenIdx: selectedIdx.value,
  })
  selectedIdx.value = null
  supplement.value = ''
}

/** 功能：函数 handleSupplementKeydown，负责 handleSupplementKeydown 相关处理。 */
function handleSupplementKeydown(e: KeyboardEvent) {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault()
    sendBranch()
  }
  if (e.key === 'Escape') {
    cancelSelection()
  }
}
</script>

<template>
  <div class="mt-3 flex flex-col gap-2" :aria-label="`故事分支选项（共 ${choices.length} 项）`">
    <!-- Header label -->
    <div class="flex items-center gap-1.5 text-xs text-muted-foreground">
      <GitBranch class="h-3 w-3" />
      <span>选择一条分支路径继续故事</span>
    </div>

    <!-- Choice cards -->
    <div
      v-for="(choice, idx) in choices"
      :key="idx"
      :class="cn(
        'rounded-xl border-2 transition-all duration-200 overflow-hidden cursor-pointer',
        generating
          ? 'opacity-50 cursor-not-allowed border-border'
          : isSelected(idx)
            ? 'border-primary bg-primary/8 shadow-md'
            : 'border-border/60 hover:border-primary/50 hover:bg-primary/4',
      )"
      @click="selectCard(idx)"
    >
      <!-- Card header row -->
      <div class="flex items-start gap-3 px-4 py-3">
        <!-- Index badge -->
        <div
          :class="cn(
            'mt-0.5 h-5 w-5 rounded-full flex items-center justify-center text-[11px] font-bold shrink-0 transition-colors',
            isSelected(idx)
              ? 'bg-primary text-primary-foreground'
              : 'bg-muted text-muted-foreground',
          )"
        >
          {{ idx + 1 }}
        </div>

        <!-- Choice text -->
        <p
          :class="cn(
            'flex-1 text-sm leading-relaxed transition-colors',
            isSelected(idx) ? 'text-foreground font-medium' : 'text-foreground/80',
          )"
        >
          {{ choice }}
        </p>

        <!-- Selected indicator -->
        <Badge
          v-if="isSelected(idx)"
          variant="outline"
          class="shrink-0 text-[10px] border-primary/40 text-primary bg-primary/5"
        >
          已选中
        </Badge>
      </div>

      <!-- Expanded zone (only when selected) -->
      <div v-if="isSelected(idx)" class="border-t border-primary/20 px-4 pb-4 pt-3 bg-primary/4">
        <!-- Supplement textarea -->
        <label class="block text-xs text-muted-foreground mb-1.5 font-medium">
          补充细节（可选）
          <span class="font-normal opacity-70 ml-1">— 补充背景、心情、装备等额外信息</span>
        </label>
        <Textarea
          ref="supplementRef"
          v-model="supplement"
          :placeholder="`在 &quot;${choice.slice(0, 20)}${choice.length > 20 ? '…' : ''}&quot; 的基础上，补充细节…`"
          class="min-h-[60px] max-h-[120px] resize-none text-sm bg-background/70 border-primary/30 focus:border-primary"
          @click.stop
          @keydown="handleSupplementKeydown"
        />

        <!-- Preview if supplement is non-empty -->
        <div v-if="supplement.trim()" class="mt-2 rounded-lg bg-muted/50 px-3 py-2 text-xs text-muted-foreground leading-relaxed border border-border/60">
          <span class="font-medium text-foreground/70 mr-1">最终发送：</span>{{ choice }}<template v-if="supplement.trim()"><br /><span class="opacity-70 italic whitespace-pre-wrap">{{ supplement.trim() }}</span></template>
        </div>

        <!-- Action buttons -->
        <div class="mt-3 flex items-center justify-end gap-2">
          <Button
            size="sm"
            variant="ghost"
            class="h-7 px-3 text-xs text-muted-foreground hover:text-destructive gap-1"
            @click.stop="cancelSelection"
          >
            <X class="h-3 w-3" />
            取消
          </Button>
          <Button
            size="sm"
            class="h-7 px-4 text-xs gap-1.5 font-medium"
            :disabled="generating"
            @click.stop="sendBranch"
          >
            <Send class="h-3 w-3" />
            发送此分支
          </Button>
        </div>
      </div>
    </div>
  </div>
</template>
