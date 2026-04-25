<script setup lang="ts">
// 文件说明：StoryView 右侧控制抽屉。
// 页面归属：
// - 渐进式创作页（/story/improv）：承担创作控制、主角人设、可选剧本参考与关键角色对白约束。
// - 剧本主导创作页（/story/scripted）：承担角色与对白相关控制，不直接负责主线推进（主线由 StoryScriptSidebar 处理）。
// 设计意义：将“生成参数编辑”从主输入区解耦，避免输入区承担过多配置操作。
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

// 组件输入参数。
// 数据来源：全部由 StoryView 持有并下发，当前组件只做展示与局部交互，不维护业务真源。
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

// 向 StoryView 回传更新事件。
// 语义约束：所有“update:*”事件都对应父层的单一数据源，避免抽屉与页面状态分叉。
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

// 主角 persona 下拉框代理。
// 意义：让模板可直接使用 v-model，同时保持父层单向数据流 + 事件回传。
const selectedPersonaModel = computed({
  get: () => props.selectedPersonaSelectValue,
  set: (value: string) => emit('update:selectedPersonaSelectValue', value),
})

// 关键角色下拉框代理（用于对白约束）。
const selectedPrincipalCharacterModel = computed({
  get: () => props.selectedPrincipalCharacterId,
  set: (value: string) => emit('update:selectedPrincipalCharacterId', value),
})

// 剧本设计选择器代理（仅用于即兴页的“可选剧本参考”）。
const selectedScriptDesignModel = computed({
  get: () => props.selectedScriptDesignId,
  set: (value: string) => emit('update:selectedScriptDesignId', value),
})

// 参考阶段选择器代理。
const selectedScriptStageModel = computed({
  get: () => props.selectedScriptStageId,
  set: (value: string) => emit('update:selectedScriptStageId', value),
})

// 参考事件选择器代理。
const selectedScriptEventModel = computed({
  get: () => props.selectedScriptEventId,
  set: (value: string) => emit('update:selectedScriptEventId', value),
})

// 是否跟随剧本设计开关代理。
const followScriptDesignModel = computed({
  get: () => props.followScriptDesign,
  set: (value: boolean) => emit('update:followScriptDesign', value),
})

// 对白模式选择器代理。
const dialogueModeModel = computed({
  get: () => props.dialogueMode,
  set: (value: 'auto' | 'focused' | 'required') => emit('update:dialogueMode', value),
})

// 对白目标输入框代理。
const dialogueTargetModel = computed({
  get: () => props.dialogueTarget,
  set: (value: string) => emit('update:dialogueTarget', value),
})

// 对白意图输入框代理。
const dialogueIntentModel = computed({
  get: () => props.dialogueIntent,
  set: (value: string) => emit('update:dialogueIntent', value),
})

// 对白风格提示输入框代理。
const dialogueStyleHintModel = computed({
  get: () => props.dialogueStyleHint,
  set: (value: string) => emit('update:dialogueStyleHint', value),
})

// 即兴模式下“剧本参考”折叠开关。
// 初始策略：若已存在剧本选择，则默认展开，帮助用户理解当前参考约束来源。
const improvScriptSectionOpen = ref(props.selectedScriptDesignId !== props.noneOptionValue)

watch(
  () => props.selectedScriptDesignId,
  (value) => {
    // 当父层在其他入口（如剧本推进面板）更新了剧本选择时，自动展开此区域，避免状态“已生效但不可见”。
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
