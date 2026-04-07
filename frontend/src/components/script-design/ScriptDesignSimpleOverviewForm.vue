<script setup lang="ts">
import { reactive, watch } from 'vue'
import { ChevronDown, Save, Sparkles } from 'lucide-vue-next'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import type { ScriptDesign, ScriptDesignUpdateInput } from '@/domains/story/api/scriptDesignApi'

const statusOptions: Array<{ value: ScriptDesign['status']; label: string }> = [
  { value: 'draft', label: '草稿' },
  { value: 'active', label: '启用中' },
  { value: 'archived', label: '已归档' },
]

interface SimpleOverviewState {
  title: string
  logline: string
  summary: string
  theme: string
  core_conflict: string
  ending_direction: string
  writing_brief: string
  protagonist_profile: string
  tone_style: string
  status: ScriptDesign['status']
  tagsText: string
  enforce_stage_order: boolean
  enforce_pending_event: boolean
  enforce_foreshadow_tracking: boolean
}

const props = defineProps<{
  design: ScriptDesign
  saving?: boolean
}>()

const emit = defineEmits<{
  save: [payload: ScriptDesignUpdateInput]
}>()

const form = reactive<SimpleOverviewState>({
  title: '',
  logline: '',
  summary: '',
  theme: '',
  core_conflict: '',
  ending_direction: '',
  writing_brief: '',
  protagonist_profile: '',
  tone_style: '',
  status: 'draft',
  tagsText: '',
  enforce_stage_order: false,
  enforce_pending_event: false,
  enforce_foreshadow_tracking: false,
})

watch(
  () => props.design,
  (design) => {
    form.title = design.title
    form.logline = design.logline ?? ''
    form.summary = design.summary ?? ''
    form.theme = design.theme ?? ''
    form.core_conflict = design.core_conflict ?? ''
    form.ending_direction = design.ending_direction ?? ''
    form.writing_brief = design.default_generation_policy.writing_brief ?? ''
    form.protagonist_profile = design.protagonist_profile ?? ''
    form.tone_style = design.tone_style ?? ''
    form.status = design.status
    form.tagsText = design.tags.join(', ')
    form.enforce_stage_order = design.default_generation_policy.enforce_stage_order
    form.enforce_pending_event = design.default_generation_policy.enforce_pending_event
    form.enforce_foreshadow_tracking = design.default_generation_policy.enforce_foreshadow_tracking
  },
  { immediate: true },
)

function submit() {
  emit('save', {
    title: form.title.trim(),
    logline: form.logline.trim() || null,
    summary: form.summary.trim() || null,
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
  <Card class="border-sky-200/80 bg-sky-50/40">
    <CardHeader>
      <CardTitle class="flex items-center gap-2">
        <Sparkles class="h-4 w-4 text-sky-600" />
        剧本信息
      </CardTitle>
      <CardDescription>聚焦普通用户最常用的剧本核心信息，先把故事方向定清楚。</CardDescription>
    </CardHeader>
    <CardContent class="space-y-4">
      <div class="grid gap-4 md:grid-cols-2">
        <div class="space-y-1.5 md:col-span-2">
          <Label for="simple-script-title">标题</Label>
          <Input id="simple-script-title" v-model="form.title" placeholder="例如：雾港疑案" />
        </div>
        <div class="space-y-1.5 md:col-span-2">
          <Label for="simple-script-logline">一句话梗概</Label>
          <Input id="simple-script-logline" v-model="form.logline" placeholder="主角为了查清港口命案，被迫卷入多方势力的暗战。" />
        </div>
        <div class="space-y-1.5 md:col-span-2">
          <Label for="simple-script-summary">故事概述</Label>
          <Textarea id="simple-script-summary" v-model="form.summary" rows="4" placeholder="用 3 到 5 句话说明故事整体走向。" />
        </div>
        <div class="space-y-1.5">
          <Label for="simple-script-theme">主题</Label>
          <Input id="simple-script-theme" v-model="form.theme" placeholder="信任与背叛" />
        </div>
        <div class="space-y-1.5">
          <Label for="simple-script-conflict">核心冲突</Label>
          <Input id="simple-script-conflict" v-model="form.core_conflict" placeholder="主角追真相，盟友要保住既得利益。" />
        </div>
        <div class="space-y-1.5 md:col-span-2">
          <Label for="simple-script-ending">结局方向</Label>
          <Input id="simple-script-ending" v-model="form.ending_direction" placeholder="揭露幕后操盘者，但代价是主角失去最信任的同伴。" />
        </div>
        <div class="space-y-1.5 md:col-span-2">
          <Label for="simple-script-brief">生成提示</Label>
          <Textarea id="simple-script-brief" v-model="form.writing_brief" rows="3" placeholder="例如：每次只推进一个关键事件，不要过早揭示幕后身份。" />
        </div>
      </div>

      <details class="group rounded-2xl border border-sky-200 bg-white/75 p-4">
        <summary class="flex cursor-pointer list-none items-center justify-between gap-3">
          <div>
            <p class="text-sm font-semibold text-slate-900">进阶补充</p>
            <p class="mt-1 text-xs text-muted-foreground">主角定位、叙事风格、标签和生成约束。需要时再展开，不打断基础信息录入。</p>
          </div>
          <span class="rounded-full border border-sky-200 bg-sky-50 p-1.5 text-sky-700 transition-transform group-open:rotate-180">
            <ChevronDown class="h-4 w-4" />
          </span>
        </summary>

        <div class="mt-4 grid gap-4 md:grid-cols-2">
          <div class="space-y-1.5">
            <Label for="advanced-script-status">状态</Label>
            <select id="advanced-script-status" v-model="form.status" class="flex h-9 w-full rounded-md border border-input bg-background px-3 py-1 text-sm shadow-sm">
              <option v-for="option in statusOptions" :key="option.value" :value="option.value">{{ option.label }}</option>
            </select>
          </div>
          <div class="space-y-1.5">
            <Label for="advanced-script-tags">标签</Label>
            <Input id="advanced-script-tags" v-model="form.tagsText" placeholder="悬疑, 长线, 权谋" />
          </div>
          <div class="space-y-1.5">
            <Label for="advanced-script-tone">叙事风格</Label>
            <Input id="advanced-script-tone" v-model="form.tone_style" placeholder="冷峻、压迫、渐进揭露" />
          </div>
          <div class="space-y-1.5 md:col-span-2">
            <Label for="advanced-script-protagonist">主角定位</Label>
            <Textarea id="advanced-script-protagonist" v-model="form.protagonist_profile" rows="2" placeholder="补充主角的角色位置、优势、短板与目标。" />
          </div>
        </div>

        <div class="mt-4 rounded-xl border border-dashed border-sky-200 bg-sky-50/60 px-4 py-3">
          <p class="text-sm font-medium text-slate-900">生成约束</p>
          <div class="mt-3 flex flex-wrap gap-4 text-sm">
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
        </div>
      </details>

      <div class="flex justify-end">
        <Button class="gap-1.5" :disabled="saving || !form.title.trim()" @click="submit">
          <Save class="h-4 w-4" />保存剧本信息
        </Button>
      </div>
    </CardContent>
  </Card>
</template>