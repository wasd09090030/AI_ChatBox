<script setup lang="ts">
import { ref, watch } from 'vue'
import { Plus, Save, Trash2 } from 'lucide-vue-next'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import type { ScriptStage } from '@/domains/story/api/scriptDesignApi'

interface StageDraft {
  id: string
  title: string
  order: number
  goal: string
  tension: string
  entry_condition: string
  exit_condition: string
  expected_turning_point: string
  notes: string
  linkedRoleIdsText: string
  linkedLorebookEntryIdsText: string
}

const props = withDefaults(defineProps<{
  stages: ScriptStage[]
  saving?: boolean
  advancedOnly?: boolean
}>(), {
  advancedOnly: false,
})

const emit = defineEmits<{
  save: [payload: ScriptStage[]]
}>()

const drafts = ref<StageDraft[]>([])

function toDraft(stage: ScriptStage): StageDraft {
  return {
    id: stage.id,
    title: stage.title,
    order: stage.order,
    goal: stage.goal ?? '',
    tension: stage.tension ?? '',
    entry_condition: stage.entry_condition ?? '',
    exit_condition: stage.exit_condition ?? '',
    expected_turning_point: stage.expected_turning_point ?? '',
    notes: stage.notes ?? '',
    linkedRoleIdsText: stage.linked_role_ids.join(', '),
    linkedLorebookEntryIdsText: stage.linked_lorebook_entry_ids.join(', '),
  }
}

watch(
  () => props.stages,
  (stages) => {
    drafts.value = stages.map(toDraft)
  },
  { immediate: true, deep: true },
)

function addStage() {
  drafts.value.push({
    id: crypto.randomUUID(),
    title: '',
    order: drafts.value.length,
    goal: '',
    tension: '',
    entry_condition: '',
    exit_condition: '',
    expected_turning_point: '',
    notes: '',
    linkedRoleIdsText: '',
    linkedLorebookEntryIdsText: '',
  })
}

function removeStage(id: string) {
  drafts.value = drafts.value.filter((stage) => stage.id !== id)
}

function submit() {
  emit('save', drafts.value.map((stage, index) => ({
    id: stage.id,
    title: stage.title.trim(),
    order: index,
    goal: stage.goal.trim() || null,
    tension: stage.tension.trim() || null,
    entry_condition: stage.entry_condition.trim() || null,
    exit_condition: stage.exit_condition.trim() || null,
    expected_turning_point: stage.expected_turning_point.trim() || null,
    linked_role_ids: stage.linkedRoleIdsText.split(',').map((item) => item.trim()).filter(Boolean),
    linked_lorebook_entry_ids: stage.linkedLorebookEntryIdsText.split(',').map((item) => item.trim()).filter(Boolean),
    notes: stage.notes.trim() || null,
  })).filter((stage) => stage.title))
}
</script>

<template>
  <Card>
    <CardHeader class="flex flex-row items-start justify-between gap-4">
      <div>
        <CardTitle>{{ props.advancedOnly ? '阶段高级设置' : '主线阶段' }}</CardTitle>
        <CardDescription>
          {{ props.advancedOnly ? '补充阶段张力、条件、关联对象和备注。' : '按顺序维护主要阶段、目标和转折点。' }}
        </CardDescription>
      </div>
      <Button v-if="!props.advancedOnly" size="sm" variant="outline" class="gap-1.5" @click="addStage">
        <Plus class="h-4 w-4" />新增阶段
      </Button>
    </CardHeader>
    <CardContent class="space-y-3">
      <div v-if="!drafts.length" class="rounded-lg border border-dashed border-border px-4 py-8 text-center text-sm text-muted-foreground">
        {{ props.advancedOnly ? '当前还没有阶段，请先在基础设置中创建阶段。' : '还没有阶段，先添加一个开场阶段。' }}
      </div>

      <div v-for="(stage, index) in drafts" :key="stage.id" class="rounded-xl border border-border p-4 space-y-3">
        <div class="flex items-center justify-between gap-2">
          <p class="text-sm font-medium">阶段 {{ index + 1 }}</p>
          <p v-if="props.advancedOnly" class="text-xs text-muted-foreground truncate">{{ stage.title || '未命名阶段' }}</p>
          <Button v-else size="sm" variant="ghost" class="h-8 px-2 text-destructive" @click="removeStage(stage.id)">
            <Trash2 class="h-4 w-4" />
          </Button>
        </div>

        <div class="grid gap-3 md:grid-cols-2">
          <div v-if="!props.advancedOnly" class="space-y-1.5 md:col-span-2">
            <Label>阶段标题</Label>
            <Input v-model="stage.title" placeholder="例如：第一幕 · 迷雾初现" />
          </div>
          <div v-if="!props.advancedOnly" class="space-y-1.5">
            <Label>阶段目标</Label>
            <Textarea v-model="stage.goal" rows="2" />
          </div>
          <div class="space-y-1.5">
            <Label>张力描述</Label>
            <Textarea v-model="stage.tension" rows="2" />
          </div>
          <div class="space-y-1.5">
            <Label>进入条件</Label>
            <Input v-model="stage.entry_condition" />
          </div>
          <div class="space-y-1.5">
            <Label>退出条件</Label>
            <Input v-model="stage.exit_condition" />
          </div>
          <div v-if="!props.advancedOnly" class="space-y-1.5 md:col-span-2">
            <Label>关键转折</Label>
            <Input v-model="stage.expected_turning_point" />
          </div>
          <div class="space-y-1.5">
            <Label>关联关键角色 ID</Label>
            <Input v-model="stage.linkedRoleIdsText" placeholder="role-1, role-2" />
          </div>
          <div class="space-y-1.5">
            <Label>关联设定条目 ID</Label>
            <Input v-model="stage.linkedLorebookEntryIdsText" placeholder="entry-1, entry-2" />
          </div>
          <div class="space-y-1.5 md:col-span-2">
            <Label>备注</Label>
            <Textarea v-model="stage.notes" rows="2" />
          </div>
        </div>
      </div>

      <div class="flex justify-end">
        <Button class="gap-1.5" :disabled="saving" @click="submit">
          <Save class="h-4 w-4" />{{ props.advancedOnly ? '保存阶段高级设置' : '保存阶段' }}
        </Button>
      </div>
    </CardContent>
  </Card>
</template>