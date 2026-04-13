<script setup lang="ts">
// 文件说明：前端可复用界面组件。
import { reactive, watch } from 'vue'
import { Save } from 'lucide-vue-next'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import type { ScriptDesign, ScriptDesignUpdateInput } from '@/domains/story/api/scriptDesignApi'

const statusOptions: Array<{ value: ScriptDesign['status']; label: string }> = [
  { value: 'draft', label: '草稿' },
  { value: 'active', label: '启用中' },
  { value: 'archived', label: '已归档' },
]

interface OverviewFormState {
  title: string
  summary: string
  logline: string
  theme: string
  core_conflict: string
  ending_direction: string
  protagonist_profile: string
  tone_style: string
  status: ScriptDesign['status']
  tagsText: string
  writing_brief: string
  enforce_stage_order: boolean
  enforce_pending_event: boolean
  enforce_foreshadow_tracking: boolean
}

// 组件输入参数。
const props = withDefaults(defineProps<{
  design: ScriptDesign
  saving?: boolean
  advancedOnly?: boolean
}>(), {
  advancedOnly: false,
})

// 组件事件派发器。
const emit = defineEmits<{
  save: [payload: ScriptDesignUpdateInput]
}>()

// form 相关状态。
const form = reactive<OverviewFormState>({
  title: '',
  summary: '',
  logline: '',
  theme: '',
  core_conflict: '',
  ending_direction: '',
  protagonist_profile: '',
  tone_style: '',
  status: 'draft',
  tagsText: '',
  writing_brief: '',
  enforce_stage_order: false,
  enforce_pending_event: false,
  enforce_foreshadow_tracking: false,
})

watch(
  () => props.design,
  (design) => {
    form.title = design.title
    form.summary = design.summary ?? ''
    form.logline = design.logline ?? ''
    form.theme = design.theme ?? ''
    form.core_conflict = design.core_conflict ?? ''
    form.ending_direction = design.ending_direction ?? ''
    form.protagonist_profile = design.protagonist_profile ?? ''
    form.tone_style = design.tone_style ?? ''
    form.status = design.status
    form.tagsText = design.tags.join(', ')
    form.writing_brief = design.default_generation_policy.writing_brief ?? ''
    form.enforce_stage_order = design.default_generation_policy.enforce_stage_order
    form.enforce_pending_event = design.default_generation_policy.enforce_pending_event
    form.enforce_foreshadow_tracking = design.default_generation_policy.enforce_foreshadow_tracking
  },
  { immediate: true },
)

/** 处理 submit 相关逻辑。 */
function submit() {
  emit('save', {
    title: form.title.trim(),
    summary: form.summary.trim() || null,
    logline: form.logline.trim() || null,
    theme: form.theme.trim() || null,
    core_conflict: form.core_conflict.trim() || null,
    ending_direction: form.ending_direction.trim() || null,
    protagonist_profile: form.protagonist_profile.trim() || null,
    tone_style: form.tone_style.trim() || null,
    status: form.status,
    tags: form.tagsText.split(',').map((item) => item.trim()).filter(Boolean),
    default_generation_policy: {
      ...props.design.default_generation_policy,
      writing_brief: form.writing_brief.trim() || null,
      enforce_stage_order: form.enforce_stage_order,
      enforce_pending_event: form.enforce_pending_event,
      enforce_foreshadow_tracking: form.enforce_foreshadow_tracking,
    },
  })
}
</script>

<template>
  <Card>
    <CardHeader>
      <CardTitle>{{ props.advancedOnly ? '高级概览设置' : '剧本概览' }}</CardTitle>
      <CardDescription>
        {{ props.advancedOnly ? '补充人物定位、风格、状态标签与默认生成约束。' : '维护主线摘要、主题、冲突与默认生成策略。' }}
      </CardDescription>
    </CardHeader>
    <CardContent class="space-y-4">
      <div class="grid gap-4 md:grid-cols-2">
        <div v-if="!props.advancedOnly" class="space-y-1.5 md:col-span-2">
          <Label for="script-title">标题</Label>
          <Input id="script-title" v-model="form.title" placeholder="例如：雾港疑案主线" />
        </div>
        <div class="space-y-1.5">
          <Label for="script-status">状态</Label>
          <select id="script-status" v-model="form.status" class="flex h-9 w-full rounded-md border border-input bg-background px-3 py-1 text-sm shadow-sm">
            <option v-for="option in statusOptions" :key="option.value" :value="option.value">{{ option.label }}</option>
          </select>
        </div>
        <div class="space-y-1.5">
          <Label for="script-tags">标签</Label>
          <Input id="script-tags" v-model="form.tagsText" placeholder="悬疑, 长线, 权谋" />
        </div>
        <div v-if="!props.advancedOnly" class="space-y-1.5 md:col-span-2">
          <Label for="script-logline">一句话梗概</Label>
          <Input id="script-logline" v-model="form.logline" placeholder="用一句话概括整个故事走向" />
        </div>
        <div v-if="!props.advancedOnly" class="space-y-1.5 md:col-span-2">
          <Label for="script-summary">总体概述</Label>
          <Textarea id="script-summary" v-model="form.summary" rows="3" />
        </div>
        <div v-if="!props.advancedOnly" class="space-y-1.5">
          <Label for="script-theme">主题</Label>
          <Input id="script-theme" v-model="form.theme" placeholder="信任、背叛、牺牲" />
        </div>
        <div v-if="!props.advancedOnly" class="space-y-1.5">
          <Label for="script-conflict">核心冲突</Label>
          <Input id="script-conflict" v-model="form.core_conflict" placeholder="主角与盟友之间的目标冲突" />
        </div>
        <div v-if="!props.advancedOnly" class="space-y-1.5">
          <Label for="script-ending">结局方向</Label>
          <Input id="script-ending" v-model="form.ending_direction" placeholder="开放、悲剧、反转收束" />
        </div>
        <div class="space-y-1.5">
          <Label for="script-tone">叙事风格</Label>
          <Input id="script-tone" v-model="form.tone_style" placeholder="冷峻、压迫、渐进揭露" />
        </div>
        <div class="space-y-1.5 md:col-span-2">
          <Label for="script-protagonist">主角定位</Label>
          <Textarea id="script-protagonist" v-model="form.protagonist_profile" rows="2" />
        </div>
        <div v-if="!props.advancedOnly" class="space-y-1.5 md:col-span-2">
          <Label for="script-brief">默认生成说明</Label>
          <Textarea id="script-brief" v-model="form.writing_brief" rows="2" placeholder="例如：优先推进当前事件，不要提前揭示幕后身份。" />
        </div>
      </div>

      <div class="flex flex-wrap gap-4 rounded-lg border border-border p-3 text-sm">
        <label class="flex items-center gap-2">
          <input v-model="form.enforce_stage_order" type="checkbox" />
          按阶段顺序推进
        </label>
        <label class="flex items-center gap-2">
          <input v-model="form.enforce_pending_event" type="checkbox" />
          优先覆盖未完成事件
        </label>
        <label class="flex items-center gap-2">
          <input v-model="form.enforce_foreshadow_tracking" type="checkbox" />
          跟踪伏笔状态
        </label>
      </div>

      <div class="flex justify-end">
        <Button class="gap-1.5" :disabled="saving || !form.title.trim()" @click="submit">
          <Save class="h-4 w-4" />{{ props.advancedOnly ? '保存高级概览' : '保存概览' }}
        </Button>
      </div>
    </CardContent>
  </Card>
</template>