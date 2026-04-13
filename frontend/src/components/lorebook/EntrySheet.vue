<script setup lang="ts">
/**
 * EntrySheet — Add or Edit a lorebook entry (character / location / event).
 *
 * Props:
 *   open       — sheet visibility
 *   type       — which entry type to show ('character' | 'location' | 'event')
 *   editing    — when truthy, holds the LorebookEntry being edited (pre-fills form)
 *   worldId    — current world id
 *
 * Emits:
 *   update:open — close signal
 *   submit      — form payload handled by parent composable
 */
import { ref, watch, computed } from 'vue'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetFooter,
} from '@/components/ui/sheet'
import type {
  LorebookEntry,
  CharacterEntryCreate,
  LocationEntryCreate,
  EventEntryCreate,
} from '@/services/lorebookService'
import type { EntrySheetSubmitPayload, EntrySheetType } from '@/domains/lorebook/types'

// 组件输入参数。
const props = defineProps<{
  open: boolean
  type: EntrySheetType
  editing: LorebookEntry | null
  worldId: string
  saving?: boolean
  defaultCharacterRoleTier?: 'npc' | 'principal'
}>()

// 组件事件派发器。
const emit = defineEmits<{
  'update:open': [v: boolean]
  submit: [payload: EntrySheetSubmitPayload]
}>()

// ── Title helpers ────────────────────────────────────────────────────────────
const LABELS: Record<EntrySheetType, string> = {
  character: '角色',
  location: '地点',
  event: '事件',
}
// sheetTitle 相关状态。
const sheetTitle = computed(() =>
  props.editing
    ? `编辑${LABELS[props.type]}条目`
    : `添加${LABELS[props.type]}条目`,
)

// ── Character form ────────────────────────────────────────────────────────────
interface CharForm {
  name: string; age: string; gender: string
  appearance: string; personality: string; background: string; speaking_style: string
  role_tier: 'npc' | 'principal'; dialogue_enabled: boolean; story_function: string
  opening_line: string; example_dialogues: string
}
// defaultChar 相关状态。
const defaultChar = (): CharForm => ({
  name: '', age: '', gender: '', appearance: '', personality: '', background: '', speaking_style: '',
  role_tier: 'npc', dialogue_enabled: false, story_function: '', opening_line: '', example_dialogues: '',
})
// charForm 相关状态。
const charForm = ref<CharForm>(defaultChar())

// ── Location form ─────────────────────────────────────────────────────────────
interface LocForm {
  name: string; description: string; region: string; climate: string; mood: string
}
// defaultLoc 相关状态。
const defaultLoc = (): LocForm => ({
  name: '', description: '', region: '', climate: '', mood: '',
})
// locForm 相关状态。
const locForm = ref<LocForm>(defaultLoc())

// ── Event form ────────────────────────────────────────────────────────────────
interface EvForm {
  name: string; description: string; time: string; location: string; importance: string
}
// defaultEv 相关状态。
const defaultEv = (): EvForm => ({
  name: '', description: '', time: '', location: '', importance: '5',
})
// evForm 相关状态。
const evForm = ref<EvForm>(defaultEv())

// ── Pre-fill from existing entry (edit mode) ──────────────────────────────────
function fillFromEntry(entry: LorebookEntry, type: EntrySheetType) {
  const m = entry.metadata as Record<string, unknown>
  if (type === 'character') {
    charForm.value = {
      name: entry.name,
      age: m.age != null ? String(m.age) : '',
      gender: String(m.gender ?? ''),
      appearance: String(m.appearance ?? ''),
      personality: String(m.personality ?? ''),
      background: String(m.background ?? ''),
      speaking_style: String(m.speaking_style ?? ''),
      role_tier: m.role_tier === 'principal' ? 'principal' : 'npc',
      dialogue_enabled: Boolean(m.dialogue_enabled ?? false),
      story_function: String(m.story_function ?? ''),
      opening_line: String(m.opening_line ?? ''),
      example_dialogues: Array.isArray(m.example_dialogues) ? m.example_dialogues.join('\n') : '',
    }
  } else if (type === 'location') {
    locForm.value = {
      name: entry.name,
      description: String(m.description ?? entry.description ?? ''),
      region: String(m.region ?? ''),
      climate: String(m.climate ?? ''),
      mood: String(m.mood ?? ''),
    }
  } else {
    evForm.value = {
      name: entry.name,
      description: String(m.description ?? entry.description ?? ''),
      time: String(m.time ?? ''),
      location: String(m.location ?? ''),
      importance: m.importance != null ? String(m.importance) : '5',
    }
  }
}

watch(
  [() => props.editing, () => props.type, () => props.defaultCharacterRoleTier],
  ([entry, type, defaultCharacterRoleTier]) => {
    charForm.value = defaultChar()
    locForm.value = defaultLoc()
    evForm.value = defaultEv()
    if (type === 'character' && !entry && defaultCharacterRoleTier === 'principal') {
      charForm.value.role_tier = 'principal'
      charForm.value.dialogue_enabled = true
    }
    if (entry) fillFromEntry(entry, type as EntrySheetType)
  },
  { immediate: true },
)

// ── Validation ────────────────────────────────────────────────────────────────
const isValid = computed(() => {
  if (props.type === 'character') return !!charForm.value.name.trim()
  if (props.type === 'location')
    return !!locForm.value.name.trim() && !!locForm.value.description.trim()
  return !!evForm.value.name.trim() && !!evForm.value.description.trim()
})

// ── Save ──────────────────────────────────────────────────────────────────────
async function save() {
  if (!props.worldId || !isValid.value) return
  emit('submit', {
    entryId: props.editing?.id ?? null,
    type: props.type,
    data: buildSubmitData(),
  })
}

/** 处理 buildSubmitData 相关逻辑。 */
function buildSubmitData(): CharacterEntryCreate | LocationEntryCreate | EventEntryCreate {
  if (props.type === 'character') {
    return {
      name: charForm.value.name.trim(),
      age: charForm.value.age ? parseInt(charForm.value.age) : null,
      gender: charForm.value.gender.trim() || null,
      appearance: charForm.value.appearance.trim() || null,
      personality: charForm.value.personality.trim() || null,
      background: charForm.value.background.trim() || null,
      speaking_style: charForm.value.speaking_style.trim() || null,
      role_tier: charForm.value.role_tier,
      dialogue_enabled: charForm.value.dialogue_enabled,
      story_function: charForm.value.story_function.trim() || null,
      opening_line: charForm.value.opening_line.trim() || null,
      example_dialogues: charForm.value.example_dialogues
        .split('\n')
        .map((line) => line.trim())
        .filter(Boolean),
    }
  }
  if (props.type === 'location') {
    return {
      name: locForm.value.name.trim(),
      description: locForm.value.description.trim(),
      region: locForm.value.region.trim() || null,
      climate: locForm.value.climate.trim() || null,
      mood: locForm.value.mood.trim() || null,
    }
  }
  return {
    name: evForm.value.name.trim(),
    description: evForm.value.description.trim(),
    time: evForm.value.time.trim() || null,
    location: evForm.value.location.trim() || null,
    importance: parseInt(evForm.value.importance) || 5,
  }
}
</script>

<template>
  <Sheet :open="open" @update:open="emit('update:open', $event)">
    <SheetContent class="w-[420px] sm:max-w-[420px] overflow-y-auto">
      <SheetHeader>
        <SheetTitle>{{ sheetTitle }}</SheetTitle>
      </SheetHeader>

      <!-- ── Character Form ─────────────────────────────── -->
      <div v-if="type === 'character'" class="mt-4 space-y-4">
        <div class="space-y-2">
          <Label>名称 <span class="text-destructive">*</span></Label>
          <Input v-model="charForm.name" placeholder="角色名称" />
        </div>
        <div class="grid grid-cols-2 gap-3">
          <div class="space-y-2">
            <Label>年龄</Label>
            <Input v-model="charForm.age" type="number" placeholder="–" />
          </div>
          <div class="space-y-2">
            <Label>性别</Label>
            <Input v-model="charForm.gender" placeholder="–" />
          </div>
        </div>
        <div class="space-y-2">
          <Label>外貌</Label>
          <Textarea v-model="charForm.appearance" placeholder="外貌描述…" class="min-h-[60px] resize-y text-sm" />
        </div>
        <div class="space-y-2">
          <Label>性格</Label>
          <Textarea v-model="charForm.personality" placeholder="性格特点…" class="min-h-[60px] resize-y text-sm" />
        </div>
        <div class="space-y-2">
          <Label>背景故事</Label>
          <Textarea v-model="charForm.background" placeholder="角色背景…" class="min-h-[80px] resize-y text-sm" />
        </div>
        <div class="space-y-2">
          <Label>说话风格</Label>
          <Input v-model="charForm.speaking_style" placeholder="例：文言文、直接…" />
        </div>
        <div class="grid grid-cols-2 gap-3">
          <div class="space-y-2">
            <Label>角色层级</Label>
            <select v-model="charForm.role_tier" class="flex h-9 w-full rounded-md border border-input bg-background px-3 py-1 text-sm shadow-sm">
              <option value="npc">普通 NPC</option>
              <option value="principal">关键角色</option>
            </select>
          </div>
          <div class="space-y-2">
            <Label>对白特化</Label>
            <label class="flex h-9 items-center gap-2 rounded-md border border-input px-3 text-sm">
              <input v-model="charForm.dialogue_enabled" type="checkbox" class="h-4 w-4" />
              允许故事中重点对白
            </label>
          </div>
        </div>
        <div class="space-y-2">
          <Label>剧情功能</Label>
          <Input v-model="charForm.story_function" placeholder="例：线索提供者、对手、情感锚点" />
        </div>
        <div class="space-y-2">
          <Label>建议开场白</Label>
          <Textarea v-model="charForm.opening_line" placeholder="首次介入故事时的建议台词…" class="min-h-[60px] resize-y text-sm" />
        </div>
        <div class="space-y-2">
          <Label>对白示例</Label>
          <Textarea v-model="charForm.example_dialogues" placeholder="每行一条示例对白…" class="min-h-[90px] resize-y text-sm" />
        </div>
      </div>

      <!-- ── Location Form ──────────────────────────────── -->
      <div v-else-if="type === 'location'" class="mt-4 space-y-4">
        <div class="space-y-2">
          <Label>名称 <span class="text-destructive">*</span></Label>
          <Input v-model="locForm.name" placeholder="地点名称" />
        </div>
        <div class="space-y-2">
          <Label>描述 <span class="text-destructive">*</span></Label>
          <Textarea v-model="locForm.description" placeholder="地点描述…" class="min-h-[80px] resize-y text-sm" />
        </div>
        <div class="grid grid-cols-2 gap-3">
          <div class="space-y-2">
            <Label>所属区域</Label>
            <Input v-model="locForm.region" placeholder="区域名称" />
          </div>
          <div class="space-y-2">
            <Label>气候</Label>
            <Input v-model="locForm.climate" placeholder="例：寒带、热带…" />
          </div>
        </div>
        <div class="space-y-2">
          <Label>氛围/情绪</Label>
          <Input v-model="locForm.mood" placeholder="例：神秘、宁静…" />
        </div>
      </div>

      <!-- ── Event Form ─────────────────────────────────── -->
      <div v-else class="mt-4 space-y-4">
        <div class="space-y-2">
          <Label>名称 <span class="text-destructive">*</span></Label>
          <Input v-model="evForm.name" placeholder="事件名称" />
        </div>
        <div class="space-y-2">
          <Label>描述 <span class="text-destructive">*</span></Label>
          <Textarea v-model="evForm.description" placeholder="事件描述…" class="min-h-[80px] resize-y text-sm" />
        </div>
        <div class="grid grid-cols-2 gap-3">
          <div class="space-y-2">
            <Label>发生时间</Label>
            <Input v-model="evForm.time" placeholder="例：第三纪元初…" />
          </div>
          <div class="space-y-2">
            <Label>发生地点</Label>
            <Input v-model="evForm.location" placeholder="地点名称" />
          </div>
        </div>
        <div class="space-y-2">
          <Label>重要程度 (1-10)</Label>
          <Input v-model="evForm.importance" type="number" min="1" max="10" />
        </div>
      </div>

      <SheetFooter class="mt-6">
        <Button variant="outline" @click="emit('update:open', false)">取消</Button>
        <Button :disabled="!isValid || props.saving" @click="save">
          {{ props.saving ? '保存中…' : (editing ? '保存修改' : '添加条目') }}
        </Button>
      </SheetFooter>
    </SheetContent>
  </Sheet>
</template>
