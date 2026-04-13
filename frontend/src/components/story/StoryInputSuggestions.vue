<script setup lang="ts">
// 文件说明：前端可复用界面组件。
import { computed, ref } from 'vue'
import { Lightbulb, Sparkles, Wand2 } from 'lucide-vue-next'
import { Button } from '@/components/ui/button'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'

interface PromptTemplate {
  id: string
  label: string
  prompt: string
}

// 组件输入参数。
const props = withDefaults(
  defineProps<{
    choices?: string[]
    disabled?: boolean
  }>(),
  {
    choices: () => [],
    disabled: false,
  },
)

// 组件事件派发器。
const emit = defineEmits<{
  (event: 'pick', prompt: string): void
  (event: 'preview-template', payload: PromptTemplate): void
}>()

// quickSuggestions 相关状态。
const quickSuggestions = computed(() => [
  '继续推进当前目标，并制造一个新的小阻碍',
  '加入一段环境细节描写，让场景更有临场感',
  '让一个 NPC 给出模糊但关键的线索',
  '在不改变主线的前提下加入情绪张力',
])

const templates: PromptTemplate[] = [
  { id: 'atmosphere-dark', label: '氛围切换：压迫', prompt: '将当前氛围切换为压迫感更强的版本，突出声音与光线变化。' },
  { id: 'atmosphere-warm', label: '氛围切换：温暖', prompt: '将当前氛围切换为温暖平静的版本，突出人物互动细节。' },
  { id: 'time-jump-short', label: '时间跳跃：短时', prompt: '将时间推进 30 分钟，保持地点和人物连续，说明发生了什么变化。' },
  { id: 'time-jump-long', label: '时间跳跃：次日', prompt: '将时间跳到第二天清晨，保持主线连续并补充过渡。' },
  { id: 'view-switch', label: '视角切换', prompt: '改为旁观者视角叙述当前场景，突出主角行为带来的影响。' },
  { id: 'plot-force', label: '强制推进主线', prompt: '让剧情向当前主线目标明显推进一步，并引入可互动的新选择点。' },
  { id: 'twist-event', label: '剧情反转', prompt: '加入一个与现有线索相关但出乎意料的转折，不要破坏逻辑。' },
  { id: 'dialogue-focus', label: '对话主导', prompt: '本轮以角色对话推动剧情，减少旁白并强化潜台词。' },
]

// selectedTemplateId 相关状态。
const selectedTemplateId = ref('')

/** 处理 emitPrompt 相关逻辑。 */
function emitPrompt(prompt: string) {
  const text = prompt.trim()
  if (!text || props.disabled) return
  emit('pick', text)
}

/** 处理 applyTemplate 相关逻辑。 */
function applyTemplate() {
  const item = templates.find((tpl) => tpl.id === selectedTemplateId.value)
  if (!item) return
  emit('preview-template', item)
}
</script>

<template>
  <div class="space-y-2 rounded-lg border border-border bg-muted/20 p-2.5">
    <div v-if="choices.length" class="space-y-1.5">
      <p class="flex items-center gap-1.5 text-[11px] font-medium text-muted-foreground">
        <Lightbulb class="h-3.5 w-3.5 text-amber-500" />
        AI 推荐行动
      </p>
      <div class="flex flex-wrap gap-1.5">
        <Button
          v-for="(choice, idx) in choices"
          :key="`${idx}-${choice}`"
          size="sm"
          variant="secondary"
          class="h-7 px-2.5 text-[11px]"
          :disabled="disabled"
          @click="emitPrompt(choice)"
        >
          {{ choice }}
        </Button>
      </div>
    </div>

    <div class="space-y-1.5">
      <p class="flex items-center gap-1.5 text-[11px] font-medium text-muted-foreground">
        <Sparkles class="h-3.5 w-3.5 text-violet-500" />
        快捷建议
      </p>
      <div class="flex flex-wrap gap-1.5">
        <Button
          v-for="item in quickSuggestions"
          :key="item"
          size="sm"
          variant="outline"
          class="h-7 px-2.5 text-[11px]"
          :disabled="disabled"
          @click="emitPrompt(item)"
        >
          {{ item }}
        </Button>
      </div>
    </div>

    <div class="space-y-1.5">
      <p class="flex items-center gap-1.5 text-[11px] font-medium text-muted-foreground">
        <Wand2 class="h-3.5 w-3.5 text-cyan-500" />
        指令模板
      </p>
      <div class="flex items-center gap-2">
        <Select v-model="selectedTemplateId">
          <SelectTrigger class="h-8 text-xs">
            <SelectValue placeholder="选择模板后先预览，再决定是否填入" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem v-for="item in templates" :key="item.id" :value="item.id">
              {{ item.label }}
            </SelectItem>
          </SelectContent>
        </Select>
        <Button
          size="sm"
          variant="default"
          class="h-8 px-3 text-xs"
          :disabled="disabled || !selectedTemplateId"
          @click="applyTemplate"
        >
          预览
        </Button>
      </div>
    </div>
  </div>
</template>

