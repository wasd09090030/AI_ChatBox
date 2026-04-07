<script setup lang="ts">
import { ref, watch } from 'vue'
import { Plus, Save, Trash2 } from 'lucide-vue-next'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import type { ScriptEventNode, ScriptStage } from '@/domains/story/api/scriptDesignApi'

const eventStatusOptions: Array<{ value: ScriptEventNode['status']; label: string }> = [
  { value: 'pending', label: '待处理' },
  { value: 'active', label: '进行中' },
  { value: 'completed', label: '已完成' },
  { value: 'skipped', label: '已跳过' },
]

const eventTypeOptions: Array<{ value: ScriptEventNode['event_type']; label: string }> = [
  { value: 'reveal', label: '揭露' },
  { value: 'conflict', label: '冲突' },
  { value: 'transition', label: '过渡' },
  { value: 'climax', label: '高潮' },
  { value: 'recovery', label: '缓冲' },
  { value: 'setup', label: '铺垫' },
  { value: 'custom', label: '自定义' },
]

interface EventDraft {
  id: string
  stage_id: string
  title: string
  summary: string
  order: number
  status: ScriptEventNode['status']
  event_type: ScriptEventNode['event_type']
  trigger_condition: string
  objective: string
  obstacle: string
  expected_outcome: string
  failure_outcome: string
  scene_hint: string
  notes: string
  participantRoleIdsText: string
  participantLorebookEntryIdsText: string
  prerequisiteEventIdsText: string
  unlocksEventIdsText: string
  foreshadowIdsText: string
}

const props = withDefaults(defineProps<{
  stages: ScriptStage[]
  events: ScriptEventNode[]
  saving?: boolean
  advancedOnly?: boolean
}>(), {
  advancedOnly: false,
})

const emit = defineEmits<{
  save: [payload: ScriptEventNode[]]
}>()

const drafts = ref<EventDraft[]>([])

function toDraft(eventNode: ScriptEventNode): EventDraft {
  return {
    id: eventNode.id,
    stage_id: eventNode.stage_id,
    title: eventNode.title,
    summary: eventNode.summary ?? '',
    order: eventNode.order,
    status: eventNode.status,
    event_type: eventNode.event_type,
    trigger_condition: eventNode.trigger_condition ?? '',
    objective: eventNode.objective ?? '',
    obstacle: eventNode.obstacle ?? '',
    expected_outcome: eventNode.expected_outcome ?? '',
    failure_outcome: eventNode.failure_outcome ?? '',
    scene_hint: eventNode.scene_hint ?? '',
    notes: eventNode.notes ?? '',
    participantRoleIdsText: eventNode.participant_role_ids.join(', '),
    participantLorebookEntryIdsText: eventNode.participant_lorebook_entry_ids.join(', '),
    prerequisiteEventIdsText: eventNode.prerequisite_event_ids.join(', '),
    unlocksEventIdsText: eventNode.unlocks_event_ids.join(', '),
    foreshadowIdsText: eventNode.foreshadow_ids.join(', '),
  }
}

watch(
  () => props.events,
  (events) => {
    drafts.value = events.map(toDraft)
  },
  { immediate: true, deep: true },
)

function addEvent() {
  drafts.value.push({
    id: crypto.randomUUID(),
    stage_id: props.stages[0]?.id ?? '',
    title: '',
    summary: '',
    order: drafts.value.length,
    status: 'pending',
    event_type: 'custom',
    trigger_condition: '',
    objective: '',
    obstacle: '',
    expected_outcome: '',
    failure_outcome: '',
    scene_hint: '',
    notes: '',
    participantRoleIdsText: '',
    participantLorebookEntryIdsText: '',
    prerequisiteEventIdsText: '',
    unlocksEventIdsText: '',
    foreshadowIdsText: '',
  })
}

function removeEvent(id: string) {
  drafts.value = drafts.value.filter((eventNode) => eventNode.id !== id)
}

function submit() {
  emit('save', drafts.value.map((eventNode, index) => ({
    id: eventNode.id,
    stage_id: eventNode.stage_id,
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
    participant_role_ids: eventNode.participantRoleIdsText.split(',').map((item) => item.trim()).filter(Boolean),
    participant_lorebook_entry_ids: eventNode.participantLorebookEntryIdsText.split(',').map((item) => item.trim()).filter(Boolean),
    prerequisite_event_ids: eventNode.prerequisiteEventIdsText.split(',').map((item) => item.trim()).filter(Boolean),
    unlocks_event_ids: eventNode.unlocksEventIdsText.split(',').map((item) => item.trim()).filter(Boolean),
    foreshadow_ids: eventNode.foreshadowIdsText.split(',').map((item) => item.trim()).filter(Boolean),
    notes: eventNode.notes.trim() || null,
  })).filter((eventNode) => eventNode.title && eventNode.stage_id))
}
</script>

<template>
  <Card>
    <CardHeader class="flex flex-row items-start justify-between gap-4">
      <div>
        <CardTitle>{{ props.advancedOnly ? '事件高级设置' : '事件节点' }}</CardTitle>
        <CardDescription>
          {{ props.advancedOnly ? '补充事件状态、类型、触发条件、依赖关系和参与对象。' : '把阶段拆成可执行事件，并维护目标、障碍和结果。' }}
        </CardDescription>
      </div>
      <Button v-if="!props.advancedOnly" size="sm" variant="outline" class="gap-1.5" :disabled="!stages.length" @click="addEvent">
        <Plus class="h-4 w-4" />新增事件
      </Button>
    </CardHeader>
    <CardContent class="space-y-3">
      <div v-if="!stages.length" class="rounded-lg border border-dashed border-border px-4 py-8 text-center text-sm text-muted-foreground">
        {{ props.advancedOnly ? '请先在基础设置中创建阶段和事件。' : '请先创建阶段，再添加事件。' }}
      </div>
      <div v-else-if="!drafts.length" class="rounded-lg border border-dashed border-border px-4 py-8 text-center text-sm text-muted-foreground">
        当前还没有事件节点。
      </div>

      <div v-for="(eventNode, index) in drafts" :key="eventNode.id" class="rounded-xl border border-border p-4 space-y-3">
        <div class="flex items-center justify-between gap-2">
          <p class="text-sm font-medium">事件 {{ index + 1 }}</p>
          <p v-if="props.advancedOnly" class="text-xs text-muted-foreground truncate">
            {{ eventNode.title || '未命名事件' }}
          </p>
          <Button v-else size="sm" variant="ghost" class="h-8 px-2 text-destructive" @click="removeEvent(eventNode.id)">
            <Trash2 class="h-4 w-4" />
          </Button>
        </div>

        <div class="grid gap-3 md:grid-cols-2">
          <div v-if="!props.advancedOnly" class="space-y-1.5 md:col-span-2">
            <Label>事件标题</Label>
            <Input v-model="eventNode.title" placeholder="例如：主角在港口发现伪造通行证" />
          </div>
          <div v-if="!props.advancedOnly" class="space-y-1.5">
            <Label>所属阶段</Label>
            <select v-model="eventNode.stage_id" class="flex h-9 w-full rounded-md border border-input bg-background px-3 py-1 text-sm shadow-sm">
              <option v-for="stage in stages" :key="stage.id" :value="stage.id">
                {{ stage.title }}
              </option>
            </select>
          </div>
          <div v-else class="space-y-1.5">
            <Label>所属阶段</Label>
            <div class="flex h-9 items-center rounded-md border border-input bg-muted/30 px-3 text-sm text-muted-foreground">
              {{ stages.find((stage) => stage.id === eventNode.stage_id)?.title || '未指定阶段' }}
            </div>
          </div>
          <div class="space-y-1.5">
            <Label>状态</Label>
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
          <div v-if="!props.advancedOnly" class="space-y-1.5 md:col-span-2">
            <Label>事件概述</Label>
            <Textarea v-model="eventNode.summary" rows="2" />
          </div>
          <div class="space-y-1.5">
            <Label>触发条件</Label>
            <Input v-model="eventNode.trigger_condition" />
          </div>
          <div v-if="!props.advancedOnly" class="space-y-1.5">
            <Label>事件目标</Label>
            <Input v-model="eventNode.objective" />
          </div>
          <div v-if="!props.advancedOnly" class="space-y-1.5">
            <Label>主要阻碍</Label>
            <Input v-model="eventNode.obstacle" />
          </div>
          <div v-if="!props.advancedOnly" class="space-y-1.5">
            <Label>预期结果</Label>
            <Input v-model="eventNode.expected_outcome" />
          </div>
          <div class="space-y-1.5">
            <Label>失败结果</Label>
            <Input v-model="eventNode.failure_outcome" />
          </div>
          <div class="space-y-1.5">
            <Label>场景提示</Label>
            <Input v-model="eventNode.scene_hint" />
          </div>
          <div class="space-y-1.5 md:col-span-2">
            <Label>参与关键角色 ID</Label>
            <Input v-model="eventNode.participantRoleIdsText" placeholder="role-1, role-2" />
          </div>
          <div class="space-y-1.5 md:col-span-2">
            <Label>参与设定条目 ID</Label>
            <Input v-model="eventNode.participantLorebookEntryIdsText" placeholder="entry-1, entry-2" />
          </div>
          <div class="space-y-1.5">
            <Label>前置事件 ID</Label>
            <Input v-model="eventNode.prerequisiteEventIdsText" placeholder="event-1, event-2" />
          </div>
          <div class="space-y-1.5">
            <Label>解锁事件 ID</Label>
            <Input v-model="eventNode.unlocksEventIdsText" placeholder="event-3" />
          </div>
          <div class="space-y-1.5 md:col-span-2">
            <Label>关联伏笔 ID</Label>
            <Input v-model="eventNode.foreshadowIdsText" placeholder="foreshadow-1" />
          </div>
          <div class="space-y-1.5 md:col-span-2">
            <Label>备注</Label>
            <Textarea v-model="eventNode.notes" rows="2" />
          </div>
        </div>
      </div>

      <div class="flex justify-end">
        <Button class="gap-1.5" :disabled="saving || !stages.length" @click="submit">
          <Save class="h-4 w-4" />{{ props.advancedOnly ? '保存事件高级设置' : '保存事件' }}
        </Button>
      </div>
    </CardContent>
  </Card>
</template>