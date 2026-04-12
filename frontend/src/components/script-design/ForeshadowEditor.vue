<script setup lang="ts">
// 文件说明：前端可复用界面组件。
import { ref, watch } from 'vue'
import { Plus, Save, Trash2 } from 'lucide-vue-next'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import type { ForeshadowRecord, ScriptEventNode, ScriptStage } from '@/domains/story/api/scriptDesignApi'

const foreshadowCategoryOptions: Array<{ value: ForeshadowRecord['category']; label: string }> = [
  { value: 'object', label: '物件' },
  { value: 'identity', label: '身份' },
  { value: 'prophecy', label: '预言' },
  { value: 'relationship', label: '关系' },
  { value: 'mystery', label: '谜团' },
  { value: 'rule', label: '规则' },
  { value: 'custom', label: '自定义' },
]

const foreshadowStatusOptions: Array<{ value: ForeshadowRecord['status']; label: string }> = [
  { value: 'planted', label: '已埋设' },
  { value: 'hinted', label: '已提示' },
  { value: 'paid_off', label: '已回收' },
  { value: 'abandoned', label: '已废弃' },
]

const importanceOptions: Array<{ value: ForeshadowRecord['importance']; label: string }> = [
  { value: 'low', label: '低' },
  { value: 'medium', label: '中' },
  { value: 'high', label: '高' },
]

// 变量作用：变量 props，用于 props 相关配置或状态。
const props = withDefaults(defineProps<{
  stages: ScriptStage[]
  events: ScriptEventNode[]
  foreshadows: ForeshadowRecord[]
  saving?: boolean
  advancedOnly?: boolean
}>(), {
  advancedOnly: false,
})

// 变量作用：变量 emit，用于 emit 相关配置或状态。
const emit = defineEmits<{
  save: [payload: ForeshadowRecord[]]
}>()

interface ForeshadowDraft extends Omit<ForeshadowRecord, 'payoff_description' | 'notes'> {
  payoff_description: string
  notes: string
}

// 变量作用：变量 drafts，用于 drafts 相关配置或状态。
const drafts = ref<ForeshadowDraft[]>([])

watch(
  () => props.foreshadows,
  (foreshadows) => {
    drafts.value = foreshadows.map((item) => ({
      ...item,
      payoff_description: item.payoff_description ?? '',
      notes: item.notes ?? '',
    }))
  },
  { immediate: true, deep: true },
)

/** 功能：函数 addForeshadow，负责 addForeshadow 相关处理。 */
function addForeshadow() {
  drafts.value.push({
    id: crypto.randomUUID(),
    title: '',
    content: '',
    category: 'custom',
    planted_stage_id: props.stages[0]?.id ?? null,
    planted_event_id: null,
    expected_payoff_stage_id: null,
    expected_payoff_event_id: null,
    payoff_description: '',
    status: 'planted',
    importance: 'medium',
    notes: '',
  })
}

/** 功能：函数 removeForeshadow，负责 removeForeshadow 相关处理。 */
function removeForeshadow(id: string) {
  drafts.value = drafts.value.filter((item) => item.id !== id)
}

/** 功能：函数 submit，负责 submit 相关处理。 */
function submit() {
  emit('save', drafts.value.map((item) => ({
    ...item,
    title: item.title.trim(),
    content: item.content.trim(),
    planted_stage_id: item.planted_stage_id || null,
    planted_event_id: item.planted_event_id || null,
    expected_payoff_stage_id: item.expected_payoff_stage_id || null,
    expected_payoff_event_id: item.expected_payoff_event_id || null,
    payoff_description: item.payoff_description?.trim() || null,
    notes: item.notes?.trim() || null,
  })).filter((item) => item.title && item.content))
}
</script>

<template>
  <Card>
    <CardHeader class="flex flex-row items-start justify-between gap-4">
      <div>
        <CardTitle>{{ props.advancedOnly ? '伏笔高级设置' : '伏笔记录' }}</CardTitle>
        <CardDescription>
          {{ props.advancedOnly ? '补充伏笔分类、事件级挂载、重要性与备注。' : '记录埋设位置、回收目标和当前状态。' }}
        </CardDescription>
      </div>
      <Button v-if="!props.advancedOnly" size="sm" variant="outline" class="gap-1.5" @click="addForeshadow">
        <Plus class="h-4 w-4" />新增伏笔
      </Button>
    </CardHeader>
    <CardContent class="space-y-3">
      <div v-if="!drafts.length" class="rounded-lg border border-dashed border-border px-4 py-8 text-center text-sm text-muted-foreground">
        {{ props.advancedOnly ? '当前还没有伏笔，请先在基础设置中创建。' : '当前还没有伏笔记录。' }}
      </div>

      <div v-for="(item, index) in drafts" :key="item.id" class="rounded-xl border border-border p-4 space-y-3">
        <div class="flex items-center justify-between gap-2">
          <p class="text-sm font-medium">伏笔 {{ index + 1 }}</p>
          <p v-if="props.advancedOnly" class="text-xs text-muted-foreground truncate">{{ item.title || '未命名伏笔' }}</p>
          <Button v-else size="sm" variant="ghost" class="h-8 px-2 text-destructive" @click="removeForeshadow(item.id)">
            <Trash2 class="h-4 w-4" />
          </Button>
        </div>

        <div class="grid gap-3 md:grid-cols-2">
          <div v-if="!props.advancedOnly" class="space-y-1.5">
            <Label>名称</Label>
            <Input v-model="item.title" placeholder="例如：断裂怀表" />
          </div>
          <div class="space-y-1.5">
            <Label>分类</Label>
            <select v-model="item.category" class="flex h-9 w-full rounded-md border border-input bg-background px-3 py-1 text-sm shadow-sm">
              <option v-for="option in foreshadowCategoryOptions" :key="option.value" :value="option.value">{{ option.label }}</option>
            </select>
          </div>
          <div v-if="!props.advancedOnly" class="space-y-1.5 md:col-span-2">
            <Label>伏笔内容</Label>
            <Textarea v-model="item.content" rows="2" />
          </div>
          <div v-if="!props.advancedOnly" class="space-y-1.5">
            <Label>埋设阶段</Label>
            <select v-model="item.planted_stage_id" class="flex h-9 w-full rounded-md border border-input bg-background px-3 py-1 text-sm shadow-sm">
              <option :value="null">未指定</option>
              <option v-for="stage in stages" :key="stage.id" :value="stage.id">{{ stage.title }}</option>
            </select>
          </div>
          <div class="space-y-1.5">
            <Label>埋设事件</Label>
            <select v-model="item.planted_event_id" class="flex h-9 w-full rounded-md border border-input bg-background px-3 py-1 text-sm shadow-sm">
              <option :value="null">未指定</option>
              <option v-for="eventNode in events" :key="eventNode.id" :value="eventNode.id">{{ eventNode.title }}</option>
            </select>
          </div>
          <div v-if="!props.advancedOnly" class="space-y-1.5">
            <Label>回收阶段</Label>
            <select v-model="item.expected_payoff_stage_id" class="flex h-9 w-full rounded-md border border-input bg-background px-3 py-1 text-sm shadow-sm">
              <option :value="null">未指定</option>
              <option v-for="stage in stages" :key="stage.id" :value="stage.id">{{ stage.title }}</option>
            </select>
          </div>
          <div class="space-y-1.5">
            <Label>回收事件</Label>
            <select v-model="item.expected_payoff_event_id" class="flex h-9 w-full rounded-md border border-input bg-background px-3 py-1 text-sm shadow-sm">
              <option :value="null">未指定</option>
              <option v-for="eventNode in events" :key="eventNode.id" :value="eventNode.id">{{ eventNode.title }}</option>
            </select>
          </div>
          <div v-if="!props.advancedOnly" class="space-y-1.5">
            <Label>状态</Label>
            <select v-model="item.status" class="flex h-9 w-full rounded-md border border-input bg-background px-3 py-1 text-sm shadow-sm">
              <option v-for="option in foreshadowStatusOptions" :key="option.value" :value="option.value">{{ option.label }}</option>
            </select>
          </div>
          <div class="space-y-1.5">
            <Label>重要性</Label>
            <select v-model="item.importance" class="flex h-9 w-full rounded-md border border-input bg-background px-3 py-1 text-sm shadow-sm">
              <option v-for="option in importanceOptions" :key="option.value" :value="option.value">{{ option.label }}</option>
            </select>
          </div>
          <div v-if="!props.advancedOnly" class="space-y-1.5 md:col-span-2">
            <Label>回收说明</Label>
            <Textarea v-model="item.payoff_description" rows="2" />
          </div>
          <div class="space-y-1.5 md:col-span-2">
            <Label>备注</Label>
            <Textarea v-model="item.notes" rows="2" />
          </div>
        </div>
      </div>

      <div class="flex justify-end">
        <Button class="gap-1.5" :disabled="saving" @click="submit">
          <Save class="h-4 w-4" />{{ props.advancedOnly ? '保存伏笔高级设置' : '保存伏笔' }}
        </Button>
      </div>
    </CardContent>
  </Card>
</template>