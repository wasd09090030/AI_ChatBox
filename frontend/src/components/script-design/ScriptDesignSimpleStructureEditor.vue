<script setup lang="ts">
// 文件说明：前端可复用界面组件。
import { computed, ref, watch } from 'vue'
import { ChevronDown, Plus, Save, Sparkles, Trash2 } from 'lucide-vue-next'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import type { ForeshadowRecord, ScriptDesign, ScriptEventNode, ScriptStage } from '@/domains/story/api/scriptDesignApi'

const eventStatusOptions: Array<{ value: ScriptEventNode['status']; label: string }> = [
  { value: 'pending', label: '待推进' },
  { value: 'active', label: '进行中' },
  { value: 'completed', label: '已完成' },
  { value: 'skipped', label: '已跳过' },
]

const eventTypeOptions: Array<{ value: ScriptEventNode['event_type']; label: string }> = [
  { value: 'setup', label: '铺垫' },
  { value: 'conflict', label: '冲突' },
  { value: 'reveal', label: '揭示' },
  { value: 'transition', label: '过渡' },
  { value: 'climax', label: '高潮' },
  { value: 'recovery', label: '收束' },
  { value: 'custom', label: '自定义' },
]

const foreshadowStatusOptions: Array<{ value: ForeshadowRecord['status']; label: string }> = [
  { value: 'planted', label: '已埋设' },
  { value: 'hinted', label: '已提示' },
  { value: 'paid_off', label: '已回收' },
  { value: 'abandoned', label: '已废弃' },
]

const foreshadowCategoryOptions: Array<{ value: ForeshadowRecord['category']; label: string }> = [
  { value: 'object', label: '物件' },
  { value: 'identity', label: '身份' },
  { value: 'prophecy', label: '预言' },
  { value: 'relationship', label: '关系' },
  { value: 'mystery', label: '谜团' },
  { value: 'rule', label: '规则' },
  { value: 'custom', label: '自定义' },
]

const foreshadowImportanceOptions: Array<{ value: ForeshadowRecord['importance']; label: string }> = [
  { value: 'low', label: '低' },
  { value: 'medium', label: '中' },
  { value: 'high', label: '高' },
]

interface SimpleEventDraft {
  id: string
  title: string
  summary: string
  objective: string
  obstacle: string
  expected_outcome: string
  status: ScriptEventNode['status']
  event_type: ScriptEventNode['event_type']
  trigger_condition: string
  failure_outcome: string
  scene_hint: string
  prerequisite_event_ids_text: string
  unlocks_event_ids_text: string
  foreshadow_ids_text: string
  participant_role_ids_text: string
  participant_lorebook_entry_ids_text: string
  notes: string
}

interface SimpleStageDraft {
  id: string
  title: string
  goal: string
  expected_turning_point: string
  tension: string
  entry_condition: string
  exit_condition: string
  linked_role_ids_text: string
  linked_lorebook_entry_ids_text: string
  notes: string
  events: SimpleEventDraft[]
}

interface SimpleForeshadowDraft {
  id: string
  title: string
  content: string
  planted_stage_id: string
  planted_event_id: string
  expected_payoff_stage_id: string
  expected_payoff_event_id: string
  payoff_description: string
  status: ForeshadowRecord['status']
  category: ForeshadowRecord['category']
  importance: ForeshadowRecord['importance']
  notes: string
}

// 变量作用：变量 props，用于 props 相关配置或状态。
const props = defineProps<{
  design: ScriptDesign
  saving?: boolean
}>()

// 变量作用：变量 emit，用于 emit 相关配置或状态。
const emit = defineEmits<{
  save: [payload: { stage_outlines: ScriptStage[]; event_nodes: ScriptEventNode[]; foreshadows: ForeshadowRecord[] }]
}>()

// 变量作用：变量 stageDrafts，用于 stageDrafts 相关配置或状态。
const stageDrafts = ref<SimpleStageDraft[]>([])
// 变量作用：变量 foreshadowDrafts，用于 foreshadowDrafts 相关配置或状态。
const foreshadowDrafts = ref<SimpleForeshadowDraft[]>([])

// 变量作用：变量 stageTitleMap，用于 stageTitleMap 相关配置或状态。
const stageTitleMap = computed(() => new Map(stageDrafts.value.map((stage) => [stage.id, stage.title])))
// 变量作用：变量 eventTitleMap，用于 eventTitleMap 相关配置或状态。
const eventTitleMap = computed(() => new Map(stageDrafts.value.flatMap((stage) => stage.events.map((eventNode) => [eventNode.id, eventNode.title] as const))))

/** 功能：函数 idsToText，负责 idsToText 相关处理。 */
function idsToText(ids: string[]) {
  return ids.join(', ')
}

/** 功能：函数 textToIds，负责 textToIds 相关处理。 */
function textToIds(value: string) {
  return value.split(',').map((item) => item.trim()).filter(Boolean)
}

/** 功能：函数 toEventDraft，负责 toEventDraft 相关处理。 */
function toEventDraft(eventNode: ScriptEventNode): SimpleEventDraft {
  return {
    id: eventNode.id,
    title: eventNode.title,
    summary: eventNode.summary ?? '',
    objective: eventNode.objective ?? '',
    obstacle: eventNode.obstacle ?? '',
    expected_outcome: eventNode.expected_outcome ?? '',
    status: eventNode.status,
    event_type: eventNode.event_type,
    trigger_condition: eventNode.trigger_condition ?? '',
    failure_outcome: eventNode.failure_outcome ?? '',
    scene_hint: eventNode.scene_hint ?? '',
    prerequisite_event_ids_text: idsToText(eventNode.prerequisite_event_ids),
    unlocks_event_ids_text: idsToText(eventNode.unlocks_event_ids),
    foreshadow_ids_text: idsToText(eventNode.foreshadow_ids),
    participant_role_ids_text: idsToText(eventNode.participant_role_ids),
    participant_lorebook_entry_ids_text: idsToText(eventNode.participant_lorebook_entry_ids),
    notes: eventNode.notes ?? '',
  }
}

watch(
  () => props.design,
  (design) => {
    stageDrafts.value = design.stage_outlines
      .slice()
      .sort((a, b) => a.order - b.order)
      .map((stage) => ({
        id: stage.id,
        title: stage.title,
        goal: stage.goal ?? '',
        expected_turning_point: stage.expected_turning_point ?? '',
        tension: stage.tension ?? '',
        entry_condition: stage.entry_condition ?? '',
        exit_condition: stage.exit_condition ?? '',
        linked_role_ids_text: idsToText(stage.linked_role_ids),
        linked_lorebook_entry_ids_text: idsToText(stage.linked_lorebook_entry_ids),
        notes: stage.notes ?? '',
        events: design.event_nodes
          .filter((eventNode) => eventNode.stage_id === stage.id)
          .sort((a, b) => a.order - b.order)
          .map(toEventDraft),
      }))

    foreshadowDrafts.value = design.foreshadows.map((item) => ({
      id: item.id,
      title: item.title,
      content: item.content,
      planted_stage_id: item.planted_stage_id ?? '',
      planted_event_id: item.planted_event_id ?? '',
      expected_payoff_stage_id: item.expected_payoff_stage_id ?? '',
      expected_payoff_event_id: item.expected_payoff_event_id ?? '',
      payoff_description: item.payoff_description ?? '',
      status: item.status,
      category: item.category,
      importance: item.importance,
      notes: item.notes ?? '',
    }))
  },
  { immediate: true, deep: true },
)

/** 功能：函数 addStage，负责 addStage 相关处理。 */
function addStage() {
  stageDrafts.value.push({
    id: crypto.randomUUID(),
    title: '',
    goal: '',
    expected_turning_point: '',
    tension: '',
    entry_condition: '',
    exit_condition: '',
    linked_role_ids_text: '',
    linked_lorebook_entry_ids_text: '',
    notes: '',
    events: [],
  })
}

/** 功能：函数 removeStage，负责 removeStage 相关处理。 */
function removeStage(stageId: string) {
  stageDrafts.value = stageDrafts.value.filter((stage) => stage.id !== stageId)
  foreshadowDrafts.value = foreshadowDrafts.value.map((item) => ({
    ...item,
    planted_stage_id: item.planted_stage_id === stageId ? '' : item.planted_stage_id,
    expected_payoff_stage_id: item.expected_payoff_stage_id === stageId ? '' : item.expected_payoff_stage_id,
  }))
}

/** 功能：函数 addEvent，负责 addEvent 相关处理。 */
function addEvent(stageId: string) {
  const stage = stageDrafts.value.find((item) => item.id === stageId)
  if (!stage) return
  stage.events.push({
    id: crypto.randomUUID(),
    title: '',
    summary: '',
    objective: '',
    obstacle: '',
    expected_outcome: '',
    status: 'pending',
    event_type: 'custom',
    trigger_condition: '',
    failure_outcome: '',
    scene_hint: '',
    prerequisite_event_ids_text: '',
    unlocks_event_ids_text: '',
    foreshadow_ids_text: '',
    participant_role_ids_text: '',
    participant_lorebook_entry_ids_text: '',
    notes: '',
  })
}

/** 功能：函数 removeEvent，负责 removeEvent 相关处理。 */
function removeEvent(stageId: string, eventId: string) {
  const stage = stageDrafts.value.find((item) => item.id === stageId)
  if (!stage) return
  stage.events = stage.events.filter((eventNode) => eventNode.id !== eventId)
  foreshadowDrafts.value = foreshadowDrafts.value.map((item) => ({
    ...item,
    planted_event_id: item.planted_event_id === eventId ? '' : item.planted_event_id,
    expected_payoff_event_id: item.expected_payoff_event_id === eventId ? '' : item.expected_payoff_event_id,
  }))
}

/** 功能：函数 addForeshadow，负责 addForeshadow 相关处理。 */
function addForeshadow() {
  foreshadowDrafts.value.push({
    id: crypto.randomUUID(),
    title: '',
    content: '',
    planted_stage_id: stageDrafts.value[0]?.id ?? '',
    planted_event_id: '',
    expected_payoff_stage_id: '',
    expected_payoff_event_id: '',
    payoff_description: '',
    status: 'planted',
    category: 'custom',
    importance: 'medium',
    notes: '',
  })
}

/** 功能：函数 removeForeshadow，负责 removeForeshadow 相关处理。 */
function removeForeshadow(id: string) {
  foreshadowDrafts.value = foreshadowDrafts.value.filter((item) => item.id !== id)
}

/** 功能：函数 submit，负责 submit 相关处理。 */
function submit() {
  const stage_outlines: ScriptStage[] = stageDrafts.value
    .map((stage, index) => ({
      id: stage.id,
      title: stage.title.trim(),
      order: index,
      goal: stage.goal.trim() || null,
      expected_turning_point: stage.expected_turning_point.trim() || null,
      tension: stage.tension.trim() || null,
      entry_condition: stage.entry_condition.trim() || null,
      exit_condition: stage.exit_condition.trim() || null,
      linked_role_ids: textToIds(stage.linked_role_ids_text),
      linked_lorebook_entry_ids: textToIds(stage.linked_lorebook_entry_ids_text),
      notes: stage.notes.trim() || null,
    }))
    .filter((stage) => stage.title)

  const validStageIds = new Set(stage_outlines.map((stage) => stage.id))

  const event_nodes: ScriptEventNode[] = stageDrafts.value.flatMap((stage) =>
    stage.events
      .map((eventNode, index) => ({
        id: eventNode.id,
        stage_id: stage.id,
        title: eventNode.title.trim(),
        summary: eventNode.summary.trim() || null,
        order: index,
        status: eventNode.status,
        event_type: eventNode.event_type,
        trigger_condition: eventNode.trigger_condition.trim() || null,
        objective: eventNode.objective.trim() || null,
        obstacle: eventNode.obstacle.trim() || null,
        expected_outcome: eventNode.expected_outcome.trim() || null,
        failure_outcome: eventNode.failure_outcome.trim() || null,
        scene_hint: eventNode.scene_hint.trim() || null,
        participant_role_ids: textToIds(eventNode.participant_role_ids_text),
        participant_lorebook_entry_ids: textToIds(eventNode.participant_lorebook_entry_ids_text),
        prerequisite_event_ids: textToIds(eventNode.prerequisite_event_ids_text),
        unlocks_event_ids: textToIds(eventNode.unlocks_event_ids_text),
        foreshadow_ids: textToIds(eventNode.foreshadow_ids_text),
        notes: eventNode.notes.trim() || null,
      }))
      .filter((eventNode) => eventNode.title && validStageIds.has(eventNode.stage_id)),
  )

  const validEventIds = new Set(event_nodes.map((eventNode) => eventNode.id))

  const foreshadows: ForeshadowRecord[] = foreshadowDrafts.value
    .map((item) => ({
      id: item.id,
      title: item.title.trim(),
      content: item.content.trim(),
      category: item.category,
      planted_stage_id: item.planted_stage_id && validStageIds.has(item.planted_stage_id) ? item.planted_stage_id : null,
      planted_event_id: item.planted_event_id && validEventIds.has(item.planted_event_id) ? item.planted_event_id : null,
      expected_payoff_stage_id: item.expected_payoff_stage_id && validStageIds.has(item.expected_payoff_stage_id) ? item.expected_payoff_stage_id : null,
      expected_payoff_event_id: item.expected_payoff_event_id && validEventIds.has(item.expected_payoff_event_id) ? item.expected_payoff_event_id : null,
      payoff_description: item.payoff_description.trim() || null,
      status: item.status,
      importance: item.importance,
      notes: item.notes.trim() || null,
    }))
    .filter((item) => item.title && item.content)

  emit('save', { stage_outlines, event_nodes, foreshadows })
}
</script>

<template>
  <Card class="border-amber-200/80 bg-amber-50/35">
    <CardHeader>
      <CardTitle class="flex items-center gap-2">
        <Sparkles class="h-4 w-4 text-amber-600" />
        主线结构
      </CardTitle>
      <CardDescription>按“阶段 → 关键事件 → 重要伏笔”搭建故事骨架，进阶字段直接放在对应条目内部展开。</CardDescription>
    </CardHeader>
    <CardContent class="space-y-5">
      <div class="flex items-center justify-between gap-3">
        <div>
          <p class="text-sm font-medium">主线阶段</p>
          <p class="mt-1 text-xs text-muted-foreground">建议先列 3 到 5 个阶段，每个阶段放 1 到 3 个关键事件。</p>
        </div>
        <Button size="sm" variant="outline" class="gap-1.5" @click="addStage">
          <Plus class="h-4 w-4" />新增阶段
        </Button>
      </div>

      <div v-if="!stageDrafts.length" class="rounded-lg border border-dashed border-border bg-background/70 px-4 py-8 text-center text-sm text-muted-foreground">
        还没有阶段，先添加一个开场阶段。
      </div>

      <div v-for="(stage, stageIndex) in stageDrafts" :key="stage.id" class="space-y-4 rounded-2xl border border-border bg-background/90 p-4 shadow-sm">
        <div class="flex items-start justify-between gap-3">
          <div>
            <p class="text-sm font-semibold">阶段 {{ stageIndex + 1 }}</p>
            <p class="mt-1 text-xs text-muted-foreground">{{ stageTitleMap.get(stage.id) || '未命名阶段' }}</p>
          </div>
          <Button size="sm" variant="ghost" class="h-8 px-2 text-destructive" @click="removeStage(stage.id)">
            <Trash2 class="h-4 w-4" />
          </Button>
        </div>

        <div class="grid gap-3 md:grid-cols-2">
          <div class="space-y-1.5 md:col-span-2">
            <Label>阶段标题</Label>
            <Input v-model="stage.title" placeholder="例如：第一幕 · 迷雾初现" />
          </div>
          <div class="space-y-1.5">
            <Label>阶段目标</Label>
            <Textarea v-model="stage.goal" rows="2" placeholder="这个阶段最重要的推进目标是什么？" />
          </div>
          <div class="space-y-1.5">
            <Label>关键转折</Label>
            <Textarea v-model="stage.expected_turning_point" rows="2" placeholder="这个阶段结束时要发生的转折。" />
          </div>
        </div>

        <details class="group rounded-xl border border-amber-200 bg-amber-50/50 p-3">
          <summary class="flex cursor-pointer list-none items-center justify-between gap-3">
            <div>
              <p class="text-sm font-medium text-slate-900">阶段高级设置</p>
              <p class="mt-1 text-xs text-muted-foreground">阶段张力、进入退出条件、关联角色与备注。</p>
            </div>
            <span class="rounded-full border border-amber-200 bg-white p-1.5 text-amber-700 transition-transform group-open:rotate-180">
              <ChevronDown class="h-4 w-4" />
            </span>
          </summary>

          <div class="mt-4 grid gap-3 md:grid-cols-2">
            <div class="space-y-1.5">
              <Label>阶段张力</Label>
              <Input v-model="stage.tension" placeholder="例如：压迫感逐步升高" />
            </div>
            <div class="space-y-1.5">
              <Label>进入条件</Label>
              <Input v-model="stage.entry_condition" placeholder="什么前置状态下进入本阶段" />
            </div>
            <div class="space-y-1.5">
              <Label>退出条件</Label>
              <Input v-model="stage.exit_condition" placeholder="达到什么状态后离开本阶段" />
            </div>
            <div class="space-y-1.5">
              <Label>关联角色 ID</Label>
              <Input v-model="stage.linked_role_ids_text" placeholder="role-a, role-b" />
            </div>
            <div class="space-y-1.5 md:col-span-2">
              <Label>关联设定条目 ID</Label>
              <Input v-model="stage.linked_lorebook_entry_ids_text" placeholder="lore-1, lore-2" />
            </div>
            <div class="space-y-1.5 md:col-span-2">
              <Label>阶段备注</Label>
              <Textarea v-model="stage.notes" rows="2" placeholder="记录这个阶段的调度说明或写作提醒。" />
            </div>
          </div>
        </details>

        <div class="space-y-3 rounded-xl border border-dashed border-amber-200 bg-amber-50/40 p-3">
          <div class="flex items-center justify-between gap-3">
            <div>
              <p class="text-sm font-medium">关键事件</p>
              <p class="mt-1 text-xs text-muted-foreground">每个阶段只保留最关键的几个事件，避免把枝节写满。</p>
            </div>
            <Button size="sm" variant="outline" class="gap-1.5" @click="addEvent(stage.id)">
              <Plus class="h-4 w-4" />新增事件
            </Button>
          </div>

          <div v-if="!stage.events.length" class="rounded-lg border border-dashed border-border bg-background/80 px-4 py-5 text-center text-sm text-muted-foreground">
            当前阶段还没有关键事件。
          </div>

          <div v-for="(eventNode, eventIndex) in stage.events" :key="eventNode.id" class="space-y-3 rounded-xl border border-border bg-background px-3 py-3">
            <div class="flex items-center justify-between gap-2">
              <p class="text-sm font-medium">事件 {{ eventIndex + 1 }}</p>
              <Button size="sm" variant="ghost" class="h-8 px-2 text-destructive" @click="removeEvent(stage.id, eventNode.id)">
                <Trash2 class="h-4 w-4" />
              </Button>
            </div>
            <div class="grid gap-3 md:grid-cols-2">
              <div class="space-y-1.5 md:col-span-2">
                <Label>事件标题</Label>
                <Input v-model="eventNode.title" placeholder="例如：主角在港口找到第一条硬线索" />
              </div>
              <div class="space-y-1.5 md:col-span-2">
                <Label>事件概述</Label>
                <Textarea v-model="eventNode.summary" rows="2" placeholder="用 1 到 3 句话描述这个事件会发生什么。" />
              </div>
              <div class="space-y-1.5">
                <Label>事件目标</Label>
                <Input v-model="eventNode.objective" placeholder="主角要达成什么" />
              </div>
              <div class="space-y-1.5">
                <Label>主要阻碍</Label>
                <Input v-model="eventNode.obstacle" placeholder="最大的阻碍是什么" />
              </div>
              <div class="space-y-1.5 md:col-span-2">
                <Label>预期结果</Label>
                <Input v-model="eventNode.expected_outcome" placeholder="这个事件结束后，故事状态应如何变化" />
              </div>
            </div>

            <details class="group rounded-lg border border-slate-200 bg-slate-50/70 p-3">
              <summary class="flex cursor-pointer list-none items-center justify-between gap-3">
                <div>
                  <p class="text-sm font-medium text-slate-900">事件高级设置</p>
                  <p class="mt-1 text-xs text-muted-foreground">类型、触发条件、失败结果、依赖关系与挂接伏笔。</p>
                </div>
                <span class="rounded-full border border-slate-200 bg-white p-1.5 text-slate-700 transition-transform group-open:rotate-180">
                  <ChevronDown class="h-4 w-4" />
                </span>
              </summary>

              <div class="mt-4 grid gap-3 md:grid-cols-2">
                <div class="space-y-1.5">
                  <Label>事件状态</Label>
                  <select v-model="eventNode.status" class="flex h-9 w-full rounded-md border border-input bg-background px-3 py-1 text-sm shadow-sm">
                    <option v-for="option in eventStatusOptions" :key="option.value" :value="option.value">{{ option.label }}</option>
                  </select>
                </div>
                <div class="space-y-1.5">
                  <Label>事件类型</Label>
                  <select v-model="eventNode.event_type" class="flex h-9 w-full rounded-md border border-input bg-background px-3 py-1 text-sm shadow-sm">
                    <option v-for="option in eventTypeOptions" :key="option.value" :value="option.value">{{ option.label }}</option>
                  </select>
                </div>
                <div class="space-y-1.5 md:col-span-2">
                  <Label>触发条件</Label>
                  <Input v-model="eventNode.trigger_condition" placeholder="满足什么条件后该事件应被触发" />
                </div>
                <div class="space-y-1.5">
                  <Label>失败结果</Label>
                  <Input v-model="eventNode.failure_outcome" placeholder="如果推进失败，会发生什么" />
                </div>
                <div class="space-y-1.5">
                  <Label>场景提示</Label>
                  <Input v-model="eventNode.scene_hint" placeholder="例如：雨夜码头、密闭议事厅" />
                </div>
                <div class="space-y-1.5">
                  <Label>前置事件 ID</Label>
                  <Input v-model="eventNode.prerequisite_event_ids_text" placeholder="event-a, event-b" />
                </div>
                <div class="space-y-1.5">
                  <Label>解锁事件 ID</Label>
                  <Input v-model="eventNode.unlocks_event_ids_text" placeholder="event-c, event-d" />
                </div>
                <div class="space-y-1.5">
                  <Label>关联伏笔 ID</Label>
                  <Input v-model="eventNode.foreshadow_ids_text" placeholder="foreshadow-a, foreshadow-b" />
                </div>
                <div class="space-y-1.5">
                  <Label>参与角色 ID</Label>
                  <Input v-model="eventNode.participant_role_ids_text" placeholder="role-a, role-b" />
                </div>
                <div class="space-y-1.5 md:col-span-2">
                  <Label>参与设定条目 ID</Label>
                  <Input v-model="eventNode.participant_lorebook_entry_ids_text" placeholder="lore-a, lore-b" />
                </div>
                <div class="space-y-1.5 md:col-span-2">
                  <Label>事件备注</Label>
                  <Textarea v-model="eventNode.notes" rows="2" placeholder="记录该事件的调度说明、出场条件或写作提醒。" />
                </div>
              </div>
            </details>
          </div>
        </div>
      </div>

      <div class="space-y-3 rounded-2xl border border-border bg-background/90 p-4 shadow-sm">
        <div class="flex items-center justify-between gap-3">
          <div>
            <p class="text-sm font-semibold">重要伏笔</p>
            <p class="mt-1 text-xs text-muted-foreground">这里只记录最关键的伏笔，细分类与事件级绑定放到高级设置。</p>
          </div>
          <Button size="sm" variant="outline" class="gap-1.5" @click="addForeshadow">
            <Plus class="h-4 w-4" />新增伏笔
          </Button>
        </div>

        <div v-if="!foreshadowDrafts.length" class="rounded-lg border border-dashed border-border px-4 py-6 text-center text-sm text-muted-foreground">
          当前还没有重要伏笔。
        </div>

        <div v-for="(item, index) in foreshadowDrafts" :key="item.id" class="space-y-3 rounded-xl border border-border p-3">
          <div class="flex items-center justify-between gap-2">
            <p class="text-sm font-medium">伏笔 {{ index + 1 }}</p>
            <Button size="sm" variant="ghost" class="h-8 px-2 text-destructive" @click="removeForeshadow(item.id)">
              <Trash2 class="h-4 w-4" />
            </Button>
          </div>
          <div class="grid gap-3 md:grid-cols-2">
            <div class="space-y-1.5">
              <Label>名称</Label>
              <Input v-model="item.title" placeholder="例如：断裂怀表" />
            </div>
            <div class="space-y-1.5">
              <Label>当前状态</Label>
              <select v-model="item.status" class="flex h-9 w-full rounded-md border border-input bg-background px-3 py-1 text-sm shadow-sm">
                <option v-for="option in foreshadowStatusOptions" :key="option.value" :value="option.value">{{ option.label }}</option>
              </select>
            </div>
            <div class="space-y-1.5 md:col-span-2">
              <Label>伏笔内容</Label>
              <Textarea v-model="item.content" rows="2" placeholder="它是什么，为什么重要。" />
            </div>
            <div class="space-y-1.5">
              <Label>埋设阶段</Label>
              <select v-model="item.planted_stage_id" class="flex h-9 w-full rounded-md border border-input bg-background px-3 py-1 text-sm shadow-sm">
                <option value="">未指定</option>
                <option v-for="stage in stageDrafts" :key="stage.id" :value="stage.id">{{ stage.title || `阶段 ${stageDrafts.findIndex((draft) => draft.id === stage.id) + 1}` }}</option>
              </select>
            </div>
            <div class="space-y-1.5">
              <Label>回收阶段</Label>
              <select v-model="item.expected_payoff_stage_id" class="flex h-9 w-full rounded-md border border-input bg-background px-3 py-1 text-sm shadow-sm">
                <option value="">未指定</option>
                <option v-for="stage in stageDrafts" :key="stage.id" :value="stage.id">{{ stage.title || `阶段 ${stageDrafts.findIndex((draft) => draft.id === stage.id) + 1}` }}</option>
              </select>
            </div>
            <div class="space-y-1.5 md:col-span-2">
              <Label>回收说明</Label>
              <Textarea v-model="item.payoff_description" rows="2" placeholder="后续准备怎么回收这个伏笔。" />
            </div>
          </div>

          <details class="group rounded-lg border border-slate-200 bg-slate-50/70 p-3">
            <summary class="flex cursor-pointer list-none items-center justify-between gap-3">
              <div>
                <p class="text-sm font-medium text-slate-900">伏笔高级设置</p>
                <p class="mt-1 text-xs text-muted-foreground">细分类、事件级绑定、重要性和补充说明。</p>
              </div>
              <span class="rounded-full border border-slate-200 bg-white p-1.5 text-slate-700 transition-transform group-open:rotate-180">
                <ChevronDown class="h-4 w-4" />
              </span>
            </summary>

            <div class="mt-4 grid gap-3 md:grid-cols-2">
              <div class="space-y-1.5">
                <Label>伏笔分类</Label>
                <select v-model="item.category" class="flex h-9 w-full rounded-md border border-input bg-background px-3 py-1 text-sm shadow-sm">
                  <option v-for="option in foreshadowCategoryOptions" :key="option.value" :value="option.value">{{ option.label }}</option>
                </select>
              </div>
              <div class="space-y-1.5">
                <Label>重要性</Label>
                <select v-model="item.importance" class="flex h-9 w-full rounded-md border border-input bg-background px-3 py-1 text-sm shadow-sm">
                  <option v-for="option in foreshadowImportanceOptions" :key="option.value" :value="option.value">{{ option.label }}</option>
                </select>
              </div>
              <div class="space-y-1.5">
                <Label>埋设事件</Label>
                <select v-model="item.planted_event_id" class="flex h-9 w-full rounded-md border border-input bg-background px-3 py-1 text-sm shadow-sm">
                  <option value="">未指定</option>
                  <option v-for="stage in stageDrafts" :key="`${item.id}-${stage.id}-planted-group`" disabled>
                    {{ stage.title || `阶段 ${stageDrafts.findIndex((draft) => draft.id === stage.id) + 1}` }}
                  </option>
                  <option v-for="stage in stageDrafts.flatMap((draft) => draft.events)" :key="stage.id" :value="stage.id">{{ eventTitleMap.get(stage.id) || stage.id }}</option>
                </select>
              </div>
              <div class="space-y-1.5">
                <Label>回收事件</Label>
                <select v-model="item.expected_payoff_event_id" class="flex h-9 w-full rounded-md border border-input bg-background px-3 py-1 text-sm shadow-sm">
                  <option value="">未指定</option>
                  <option v-for="stage in stageDrafts.flatMap((draft) => draft.events)" :key="`${stage.id}-payoff`" :value="stage.id">{{ eventTitleMap.get(stage.id) || stage.id }}</option>
                </select>
              </div>
              <div class="space-y-1.5 md:col-span-2">
                <Label>伏笔备注</Label>
                <Textarea v-model="item.notes" rows="2" placeholder="记录该伏笔的使用边界、情绪目标或后续提醒。" />
              </div>
            </div>
          </details>
        </div>
      </div>

      <div class="flex justify-end">
        <Button class="gap-1.5" :disabled="saving" @click="submit">
          <Save class="h-4 w-4" />保存主线结构
        </Button>
      </div>
    </CardContent>
  </Card>
</template>