<script setup lang="ts">
// 文件说明：前端可复用界面组件。
import { ref, watch } from 'vue'
import { X } from 'lucide-vue-next'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { Badge } from '@/components/ui/badge'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from '@/components/ui/dialog'
import type { World, WorldCreate } from '@/services/lorebookService'

// 变量作用：变量 props，用于 props 相关配置或状态。
const props = defineProps<{
  open: boolean
  editing: World | null
}>()

// 变量作用：变量 emit，用于 emit 相关配置或状态。
const emit = defineEmits<{
  'update:open': [v: boolean]
  save: [payload: WorldCreate]
}>()

interface WorldForm {
  name: string
  description: string
  genre: string
  setting: string
  rules: string
  style_tags: string[]
  narrative_tone: string
  pacing_style: string
  vocabulary_style: string
}

// 变量作用：变量 defaultForm，用于 defaultForm 相关配置或状态。
const defaultForm = (): WorldForm => ({
  name: '',
  description: '',
  genre: '',
  setting: '',
  rules: '',
  style_tags: [],
  narrative_tone: '',
  pacing_style: '',
  vocabulary_style: '',
})

// 变量作用：变量 form，用于 form 相关配置或状态。
const form = ref<WorldForm>(defaultForm())
// 变量作用：变量 newTag，用于 newTag 相关配置或状态。
const newTag = ref('')

watch(
  () => props.editing,
  (w) => {
    if (w) {
      form.value = {
        name: w.name,
        description: w.description ?? '',
        genre: w.genre ?? '',
        setting: w.setting ?? '',
        rules: w.rules ?? '',
        style_tags: [...(w.style_tags ?? [])],
        narrative_tone: w.narrative_tone ?? '',
        pacing_style: w.pacing_style ?? '',
        vocabulary_style: w.vocabulary_style ?? '',
      }
    } else {
      form.value = defaultForm()
    }
    newTag.value = ''
  },
  { immediate: true },
)

/** 功能：函数 addTag，负责 addTag 相关处理。 */
function addTag() {
  const t = newTag.value.trim()
  if (t && !form.value.style_tags.includes(t)) form.value.style_tags.push(t)
  newTag.value = ''
}

/** 功能：函数 removeTag，负责 removeTag 相关处理。 */
function removeTag(tag: string) {
  form.value.style_tags = form.value.style_tags.filter((t) => t !== tag)
}

/** 功能：函数 submit，负责 submit 相关处理。 */
function submit() {
  emit('save', {
    name: form.value.name.trim(),
    description: form.value.description.trim(),
    genre: form.value.genre.trim() || null,
    setting: form.value.setting.trim() || null,
    rules: form.value.rules.trim() || null,
    style_tags: form.value.style_tags,
    narrative_tone: form.value.narrative_tone.trim() || null,
    pacing_style: form.value.pacing_style.trim() || null,
    vocabulary_style: form.value.vocabulary_style.trim() || null,
    style_preset: null,
    default_time_of_day: null,
    default_weather: null,
    default_mood: null,
    metadata: {},
  })
}
</script>

<template>
  <Dialog :open="open" @update:open="emit('update:open', $event)">
    <DialogContent class="sm:max-w-2xl max-h-[90vh] overflow-y-auto">
      <DialogHeader>
        <DialogTitle>{{ editing ? '编辑世界' : '新建世界' }}</DialogTitle>
      </DialogHeader>

      <div class="space-y-4 py-2">
        <div class="grid grid-cols-2 gap-4">
          <div class="space-y-2">
            <Label>名称 <span class="text-destructive">*</span></Label>
            <Input v-model="form.name" placeholder="世界名称" />
          </div>
          <div class="space-y-2">
            <Label>类型/流派</Label>
            <Input v-model="form.genre" placeholder="例：玄幻、科幻、历史…" />
          </div>
        </div>

        <div class="space-y-2">
          <Label>世界描述</Label>
          <Textarea
            v-model="form.description"
            placeholder="简要描述这个世界…"
            class="min-h-[70px] resize-y text-sm"
          />
        </div>

        <div class="space-y-2">
          <Label>世界观设定</Label>
          <Textarea
            v-model="form.setting"
            placeholder="地理、历史、魔法体系等…"
            class="min-h-[80px] resize-y text-sm"
          />
        </div>

        <div class="space-y-2">
          <Label>规则限定</Label>
          <Textarea
            v-model="form.rules"
            placeholder="这个世界的特殊规则…"
            class="min-h-[60px] resize-y text-sm"
          />
        </div>

        <div class="grid grid-cols-3 gap-4">
          <div class="space-y-2">
            <Label>叙事基调</Label>
            <Input v-model="form.narrative_tone" placeholder="例：史诗、轻松…" />
          </div>
          <div class="space-y-2">
            <Label>节奏风格</Label>
            <Input v-model="form.pacing_style" placeholder="例：快节奏、平缓…" />
          </div>
          <div class="space-y-2">
            <Label>词汇风格</Label>
            <Input v-model="form.vocabulary_style" placeholder="例：古典、现代…" />
          </div>
        </div>

        <div class="space-y-2">
          <Label>风格标签</Label>
          <div class="flex flex-wrap gap-1.5 mb-2 min-h-[24px]">
            <Badge
              v-for="tag in form.style_tags"
              :key="tag"
              variant="secondary"
              class="gap-1 pr-1"
            >
              {{ tag }}
              <button class="hover:text-foreground ml-0.5" @click="removeTag(tag)">
                <X class="h-2.5 w-2.5" />
              </button>
            </Badge>
          </div>
          <div class="flex gap-2">
            <Input
              v-model="newTag"
              placeholder="添加标签…"
              class="h-8 text-sm"
              @keydown.enter.prevent="addTag"
            />
            <Button size="sm" variant="outline" @click="addTag">添加</Button>
          </div>
        </div>
      </div>

      <DialogFooter>
        <Button variant="outline" @click="emit('update:open', false)">取消</Button>
        <Button :disabled="!form.name.trim()" @click="submit">保存</Button>
      </DialogFooter>
    </DialogContent>
  </Dialog>
</template>
