<script setup lang="ts">
// 文件说明：前端可复用界面组件。
import { computed, ref, watch } from 'vue'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Sheet, SheetContent, SheetHeader, SheetTitle } from '@/components/ui/sheet'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { ChevronDown } from 'lucide-vue-next'
import StoryControlPanel from '@/components/story/StoryControlPanel.vue'
import type { StoryMode } from '@/components/story/types'
import type { LorebookEntry } from '@/services/lorebookService'
import type { PersonaProfile } from '@/services/roleplayService'
import type { ScriptDesign, ScriptEventNode, ScriptStage } from '@/domains/story/api/scriptDesignApi'

// 变量作用：变量 props，用于 props 相关配置或状态。
const props = defineProps<{
  open: boolean
  panelTitle: string
  showControlPanel: boolean
  storyMode: StoryMode
  authorsNote: string
  instruction: string
  controlBadgeText: string
  modeLabels: Record<StoryMode, string>
  selectedPersonaName: string | null
  selectedPersonaSelectValue: string
  selectedScriptDesignId: string
  selectedScriptStageId: string
  selectedScriptEventId: string
  followScriptDesign: boolean
  pageMode: 'improv' | 'scripted'
  selectedPrincipalCharacterId: string
  dialogueMode: 'auto' | 'focused' | 'required'
  dialogueTarget: string
  dialogueIntent: string
  dialogueStyleHint: string
  noneOptionValue: string
  personas?: PersonaProfile[]
  scriptDesigns?: ScriptDesign[]
  scriptStages?: ScriptStage[]
  scriptEvents?: ScriptEventNode[]
  principalCharacters?: LorebookEntry[]
  personasLoading: boolean
  generating: boolean
}>()

// 变量作用：变量 emit，用于 emit 相关配置或状态。
const emit = defineEmits<{
  (event: 'update:open', value: boolean): void
  (event: 'update:showControlPanel', value: boolean): void
  (event: 'update:storyMode', value: StoryMode): void
  (event: 'update:authorsNote', value: string): void
  (event: 'update:instruction', value: string): void
  (event: 'update:selectedPersonaSelectValue', value: string): void
  (event: 'update:selectedScriptDesignId', value: string): void
  (event: 'update:selectedScriptStageId', value: string): void
  (event: 'update:selectedScriptEventId', value: string): void
  (event: 'update:followScriptDesign', value: boolean): void
  (event: 'update:selectedPrincipalCharacterId', value: string): void
  (event: 'update:dialogueMode', value: 'auto' | 'focused' | 'required'): void
  (event: 'update:dialogueTarget', value: string): void
  (event: 'update:dialogueIntent', value: string): void
  (event: 'update:dialogueStyleHint', value: string): void
}>()

// 变量作用：变量 selectedPersonaModel，用于 selectedPersonaModel 相关配置或状态。
const selectedPersonaModel = computed({
  get: () => props.selectedPersonaSelectValue,
  set: (value: string) => emit('update:selectedPersonaSelectValue', value),
})

// 变量作用：变量 selectedPrincipalCharacterModel，用于 selectedPrincipalCharacterModel 相关配置或状态。
const selectedPrincipalCharacterModel = computed({
  get: () => props.selectedPrincipalCharacterId,
  set: (value: string) => emit('update:selectedPrincipalCharacterId', value),
})

// 变量作用：变量 selectedScriptDesignModel，用于 selectedScriptDesignModel 相关配置或状态。
const selectedScriptDesignModel = computed({
  get: () => props.selectedScriptDesignId,
  set: (value: string) => emit('update:selectedScriptDesignId', value),
})

// 变量作用：变量 selectedScriptStageModel，用于 selectedScriptStageModel 相关配置或状态。
const selectedScriptStageModel = computed({
  get: () => props.selectedScriptStageId,
  set: (value: string) => emit('update:selectedScriptStageId', value),
})

// 变量作用：变量 selectedScriptEventModel，用于 selectedScriptEventModel 相关配置或状态。
const selectedScriptEventModel = computed({
  get: () => props.selectedScriptEventId,
  set: (value: string) => emit('update:selectedScriptEventId', value),
})

// 变量作用：变量 followScriptDesignModel，用于 followScriptDesignModel 相关配置或状态。
const followScriptDesignModel = computed({
  get: () => props.followScriptDesign,
  set: (value: boolean) => emit('update:followScriptDesign', value),
})

// 变量作用：变量 dialogueModeModel，用于 dialogueModeModel 相关配置或状态。
const dialogueModeModel = computed({
  get: () => props.dialogueMode,
  set: (value: 'auto' | 'focused' | 'required') => emit('update:dialogueMode', value),
})

// 变量作用：变量 dialogueTargetModel，用于 dialogueTargetModel 相关配置或状态。
const dialogueTargetModel = computed({
  get: () => props.dialogueTarget,
  set: (value: string) => emit('update:dialogueTarget', value),
})

// 变量作用：变量 dialogueIntentModel，用于 dialogueIntentModel 相关配置或状态。
const dialogueIntentModel = computed({
  get: () => props.dialogueIntent,
  set: (value: string) => emit('update:dialogueIntent', value),
})

// 变量作用：变量 dialogueStyleHintModel，用于 dialogueStyleHintModel 相关配置或状态。
const dialogueStyleHintModel = computed({
  get: () => props.dialogueStyleHint,
  set: (value: string) => emit('update:dialogueStyleHint', value),
})

// 变量作用：变量 improvScriptSectionOpen，用于 improvScriptSectionOpen 相关配置或状态。
const improvScriptSectionOpen = ref(props.selectedScriptDesignId !== props.noneOptionValue)

watch(
  () => props.selectedScriptDesignId,
  (value) => {
    if (value !== props.noneOptionValue) {
      improvScriptSectionOpen.value = true
    }
  },
  { immediate: true },
)
</script>

<template>
  <Sheet :open="open" @update:open="emit('update:open', $event)">
    <SheetContent side="right" class="w-[36rem] sm:max-w-[36rem] p-0 flex flex-col">
      <SheetHeader class="border-b border-border px-5 py-4 text-left">
        <SheetTitle>{{ panelTitle }}</SheetTitle>
      </SheetHeader>

      <ScrollArea class="flex-1">
        <div class="space-y-5 px-5 py-4">
          <StoryControlPanel
            v-if="pageMode === 'improv'"
            :show="showControlPanel"
            :collapsible="false"
            :story-mode="storyMode"
            :authors-note="authorsNote"
            :instruction="instruction"
            :control-badge-text="controlBadgeText"
            :mode-labels="modeLabels"
            @update:show="emit('update:showControlPanel', $event)"
            @update:story-mode="emit('update:storyMode', $event)"
            @update:authors-note="emit('update:authorsNote', $event)"
            @update:instruction="emit('update:instruction', $event)"
          />

          <section class="space-y-3 rounded-lg border border-border/70 bg-background p-4">
            <div class="flex items-center justify-between gap-3">
              <div class="min-w-0">
                <p class="text-sm font-medium text-foreground">主角人设</p>
                <p class="mt-1 text-xs text-muted-foreground">
                  <template v-if="selectedPersonaName">当前人设：{{ selectedPersonaName }}</template>
                  <template v-else>未选择时，默认主角就是你自己。</template>
                </p>
              </div>
              <div class="w-56 shrink-0">
                <Select v-model="selectedPersonaModel" :disabled="generating || personasLoading">
                  <SelectTrigger class="h-8 text-xs">
                    <SelectValue placeholder="选择主角人设（可选）" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem :value="noneOptionValue">默认：用户自己</SelectItem>
                    <SelectItem
                      v-for="persona in personas ?? []"
                      :key="persona.id"
                      :value="persona.id"
                    >
                      {{ persona.name }}
                    </SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>
          </section>

          <section v-if="pageMode === 'improv'" class="rounded-lg border border-border/70 bg-background">
            <button
              type="button"
              class="flex w-full items-center justify-between gap-3 px-4 py-3 text-left"
              @click="improvScriptSectionOpen = !improvScriptSectionOpen"
            >
              <div class="space-y-1">
                <p class="text-sm font-medium text-foreground">剧本设计（可选）</p>
                <p class="text-xs text-muted-foreground">需要时再展开，把剧本作为渐进式创作的参考约束。</p>
              </div>
              <ChevronDown class="h-4 w-4 shrink-0 transition-transform" :class="improvScriptSectionOpen && 'rotate-180'" />
            </button>

            <div v-if="improvScriptSectionOpen" class="space-y-3 border-t border-border/70 px-4 py-4">
              <div class="space-y-2">
                <Label class="text-xs text-muted-foreground">参考剧本</Label>
                <Select v-model="selectedScriptDesignModel" :disabled="generating">
                  <SelectTrigger class="h-8 text-xs">
                    <SelectValue placeholder="不指定剧本设计" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem :value="noneOptionValue">不指定剧本设计</SelectItem>
                    <SelectItem
                      v-for="design in scriptDesigns ?? []"
                      :key="design.id"
                      :value="design.id"
                    >
                      {{ design.title }}
                    </SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <div v-if="selectedScriptDesignId !== noneOptionValue" class="grid gap-3">
                <label class="flex items-center gap-2 text-xs text-foreground">
                  <input v-model="followScriptDesignModel" type="checkbox" :disabled="generating" />
                  按当前剧本设计推进本轮内容
                </label>

                <div class="space-y-2">
                  <Label class="text-xs text-muted-foreground">参考阶段</Label>
                  <Select v-model="selectedScriptStageModel" :disabled="generating">
                    <SelectTrigger class="h-8 text-xs">
                      <SelectValue placeholder="自动选择阶段" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem :value="noneOptionValue">自动选择阶段</SelectItem>
                      <SelectItem
                        v-for="stage in scriptStages ?? []"
                        :key="stage.id"
                        :value="stage.id"
                      >
                        {{ stage.title }}
                      </SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                <div class="space-y-2">
                  <Label class="text-xs text-muted-foreground">参考事件</Label>
                  <Select v-model="selectedScriptEventModel" :disabled="generating">
                    <SelectTrigger class="h-8 text-xs">
                      <SelectValue placeholder="自动选择事件" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem :value="noneOptionValue">自动选择事件</SelectItem>
                      <SelectItem
                        v-for="eventNode in scriptEvents ?? []"
                        :key="eventNode.id"
                        :value="eventNode.id"
                      >
                        {{ eventNode.title }}
                      </SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>
            </div>
          </section>

          <section class="space-y-3 rounded-lg border border-border/70 bg-background p-4">
            <div class="space-y-1">
              <p class="text-sm font-medium text-foreground">关键角色交流</p>
              <p class="text-xs text-muted-foreground">从当前世界的 Lorebook 角色中选择本轮重点交流对象，并约束对白出现方式。</p>
            </div>

            <div class="grid gap-3">
              <div class="space-y-2">
                <Label class="text-xs text-muted-foreground">关键角色</Label>
                <Select v-model="selectedPrincipalCharacterModel" :disabled="generating">
                  <SelectTrigger class="h-8 text-xs">
                    <SelectValue placeholder="不指定关键角色" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem :value="noneOptionValue">不指定关键角色</SelectItem>
                    <SelectItem
                      v-for="entry in principalCharacters ?? []"
                      :key="entry.id ?? entry.name"
                      :value="entry.id ?? entry.name"
                    >
                      {{ entry.name }}
                    </SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <div class="space-y-2">
                <Label class="text-xs text-muted-foreground">对白模式</Label>
                <Select v-model="dialogueModeModel" :disabled="generating">
                  <SelectTrigger class="h-8 text-xs">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="auto">自动融入</SelectItem>
                    <SelectItem value="focused">优先发言</SelectItem>
                    <SelectItem value="required">本轮必须对白</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <div class="space-y-2">
                <Label class="text-xs text-muted-foreground">对话目标</Label>
                <Input v-model="dialogueTargetModel" class="h-8 text-xs" placeholder="例：主角、导师、守卫队长" />
              </div>

              <div class="space-y-2">
                <Label class="text-xs text-muted-foreground">交流意图</Label>
                <Input v-model="dialogueIntentModel" class="h-8 text-xs" placeholder="例：透露情报、施压、试探、缓和关系" />
              </div>

              <div class="space-y-2">
                <Label class="text-xs text-muted-foreground">风格提示</Label>
                <Textarea v-model="dialogueStyleHintModel" class="min-h-[72px] text-xs resize-none" placeholder="例：保持压迫感，话少但句句带刺；避免长篇解释。" />
              </div>
            </div>
          </section>
        </div>
      </ScrollArea>
    </SheetContent>
  </Sheet>
</template>
