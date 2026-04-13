<script setup lang="ts">
// 文件说明：前端可复用界面组件。
import { computed } from 'vue'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Sheet, SheetContent, SheetFooter, SheetHeader, SheetTitle } from '@/components/ui/sheet'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { cn } from '@/lib/utils'
import type { PromptFocusTemplate } from '@/config/prompts'
import type { ComposerTab } from '@/domains/story/composables/useStoryPromptComposer'
import type { LorebookEntry } from '@/services/lorebookService'

// 组件输入参数。
const props = defineProps<{
  open: boolean
  generating: boolean
  selectedContextEntries: LorebookEntry[]
  activeFocusTemplate: PromptFocusTemplate | null
  composerSearchQuery: string
  currentComposerTab: ComposerTab
  filteredCharacterEntries: LorebookEntry[]
  filteredLocationEntries: LorebookEntry[]
  filteredEventEntries: LorebookEntry[]
  composerPreviewEntry: LorebookEntry | null
  lorebookEntriesLoading: boolean
  promptFocusTemplates: PromptFocusTemplate[]
  draftFocusTemplateId: string
  isDraftEntrySelected: (entry: LorebookEntry) => boolean
}>()

// 组件事件派发器。
const emit = defineEmits<{
  (event: 'update:open', value: boolean): void
  (event: 'update:composerSearchQuery', value: string): void
  (event: 'update:currentComposerTab', value: ComposerTab): void
  (event: 'update:draftFocusTemplateId', value: string): void
  (event: 'clear'): void
  (event: 'remove-entry', entryId: string | null): void
  (event: 'clear-focus-template'): void
  (event: 'open-entry', entry: LorebookEntry): void
  (event: 'toggle-entry', entry: LorebookEntry): void
  (event: 'apply'): void
}>()

// searchQueryModel 的双向绑定状态。
const searchQueryModel = computed({
  get: () => props.composerSearchQuery,
  set: (value: string) => emit('update:composerSearchQuery', value),
})

// composerTabModel 的双向绑定状态。
const composerTabModel = computed({
  get: () => props.currentComposerTab,
  set: (value: ComposerTab) => emit('update:currentComposerTab', value),
})

// focusTemplateModel 的双向绑定状态。
const focusTemplateModel = computed({
  get: () => props.draftFocusTemplateId,
  set: (value: string) => emit('update:draftFocusTemplateId', value),
})

// entryGroups 相关状态。
const entryGroups = computed(() => [
  {
    type: 'character' as const,
    entries: props.filteredCharacterEntries,
    emptyText: '没有匹配的人物条目。',
    previewEmptyText: '点击左侧名称查看该人物内容。',
  },
  {
    type: 'location' as const,
    entries: props.filteredLocationEntries,
    emptyText: '没有匹配的地点条目。',
    previewEmptyText: '点击左侧名称查看该地点内容。',
  },
  {
    type: 'event' as const,
    entries: props.filteredEventEntries,
    emptyText: '没有匹配的事件条目。',
    previewEmptyText: '点击左侧名称查看该事件内容。',
  },
])
</script>

<template>
  <Sheet :open="open" @update:open="emit('update:open', $event)">
    <SheetContent side="right" class="w-[36rem] sm:max-w-[36rem] p-0 flex flex-col">
      <SheetHeader class="border-b border-border px-5 py-4 text-left">
        <SheetTitle>Prompt 编排</SheetTitle>
      </SheetHeader>

      <ScrollArea class="flex-1">
        <div class="space-y-5 px-5 py-4">
          <section class="space-y-3 rounded-lg border border-border/70 bg-background p-4">
            <div class="flex items-start justify-between gap-3">
              <div>
                <p class="text-sm font-medium text-foreground">Prompt 编排</p>
                <p class="mt-1 text-xs text-muted-foreground">显式选择的人物 / 地点 / 事件会优先注入本轮生成，RAG 只补充未选中的上下文。</p>
              </div>
              <Button
                v-if="selectedContextEntries.length || activeFocusTemplate"
                size="sm"
                variant="ghost"
                class="h-8 px-3 text-xs"
                :disabled="generating"
                @click="emit('clear')"
              >
                清空
              </Button>
            </div>

            <div v-if="selectedContextEntries.length || activeFocusTemplate" class="flex flex-wrap items-center gap-1.5 rounded-md border border-dashed border-border/70 bg-muted/20 px-3 py-2">
              <div
                v-for="entry in selectedContextEntries"
                :key="entry.id || entry.name"
                class="inline-flex items-center gap-1 rounded-full border border-emerald-300 bg-emerald-50 px-2 py-0.5 text-[11px] text-emerald-900"
              >
                <span>{{ entry.name }}</span>
                <button type="button" class="text-emerald-700 hover:text-emerald-950" @click="emit('remove-entry', entry.id)">
                  ×
                </button>
              </div>
              <div
                v-if="activeFocusTemplate"
                class="inline-flex items-center gap-1 rounded-full border border-sky-300 bg-sky-50 px-2 py-0.5 text-[11px] text-sky-900"
              >
                <span>{{ activeFocusTemplate.label }}</span>
                <button type="button" class="text-sky-700 hover:text-sky-950" @click="emit('clear-focus-template')">
                  ×
                </button>
              </div>
            </div>

            <div class="space-y-2">
              <Label for="prompt-composer-search">搜索条目</Label>
              <Input
                id="prompt-composer-search"
                v-model="searchQueryModel"
                placeholder="按名称或内容搜索人物 / 地点 / 事件"
                class="h-9"
              />
            </div>

            <Tabs v-model="composerTabModel" class="space-y-3">
              <TabsList class="grid w-full grid-cols-3">
                <TabsTrigger value="character">人物</TabsTrigger>
                <TabsTrigger value="location">地点</TabsTrigger>
                <TabsTrigger value="event">事件</TabsTrigger>
              </TabsList>

              <TabsContent v-for="group in entryGroups" :key="group.type" :value="group.type">
                <div class="grid h-64 grid-cols-[15rem_minmax(0,1fr)] gap-3">
                  <ScrollArea class="rounded-md border border-border/70">
                    <div class="p-2">
                      <button
                        v-for="entry in group.entries"
                        :key="entry.id || entry.name"
                        type="button"
                        :class="cn(
                          'flex w-full items-center justify-between rounded-md px-3 py-2 text-left text-sm transition-colors',
                          composerPreviewEntry?.id === entry.id
                            ? 'bg-muted text-foreground'
                            : 'text-muted-foreground hover:bg-muted/40 hover:text-foreground',
                        )"
                        @click="emit('open-entry', entry)"
                      >
                        <span class="truncate">{{ entry.name }}</span>
                        <Badge v-if="isDraftEntrySelected(entry)" variant="secondary" class="text-[10px]">已选</Badge>
                      </button>
                      <p v-if="!group.entries.length && !lorebookEntriesLoading" class="px-3 py-4 text-sm text-muted-foreground">{{ group.emptyText }}</p>
                    </div>
                  </ScrollArea>
                  <div class="rounded-md border border-border/70 bg-background p-4">
                    <template v-if="composerPreviewEntry">
                      <div class="flex items-center justify-between gap-3">
                        <div>
                          <p class="text-sm font-medium">{{ composerPreviewEntry.name }}</p>
                          <p class="text-xs text-muted-foreground">{{ composerPreviewEntry.type }}</p>
                        </div>
                        <Button size="sm" variant="outline" @click="emit('toggle-entry', composerPreviewEntry)">
                          {{ isDraftEntrySelected(composerPreviewEntry) ? '移出本轮' : '加入本轮' }}
                        </Button>
                      </div>
                      <ScrollArea class="mt-3 h-40 pr-3">
                        <p class="whitespace-pre-wrap text-sm leading-6 text-foreground">{{ composerPreviewEntry.description }}</p>
                      </ScrollArea>
                    </template>
                    <p v-else class="text-sm text-muted-foreground">{{ group.previewEmptyText }}</p>
                  </div>
                </div>
              </TabsContent>
            </Tabs>

            <div class="space-y-2">
              <p class="text-sm font-medium">本轮故事重点模板</p>
              <div class="grid grid-cols-2 gap-2">
                <button
                  v-for="item in promptFocusTemplates"
                  :key="item.id"
                  type="button"
                  :class="cn(
                    'rounded-md border p-3 text-left transition-colors',
                    focusTemplateModel === item.id
                      ? 'border-sky-500 bg-sky-50 text-sky-950'
                      : 'border-border bg-background hover:bg-muted/40',
                  )"
                  @click="focusTemplateModel = focusTemplateModel === item.id ? '' : item.id"
                >
                  <div class="flex items-center justify-between gap-2">
                    <p class="text-sm font-medium">{{ item.label }}</p>
                    <Badge v-if="focusTemplateModel === item.id" variant="secondary" class="text-[10px]">已选中</Badge>
                  </div>
                  <p class="mt-1 text-xs text-muted-foreground">{{ item.description }}</p>
                </button>
              </div>
            </div>
          </section>
        </div>
      </ScrollArea>

      <SheetFooter class="border-t border-border px-5 py-4">
        <Button variant="ghost" @click="emit('update:open', false)">取消</Button>
        <Button variant="outline" @click="emit('clear')">清空选择</Button>
        <Button @click="emit('apply')">应用到本轮 Prompt</Button>
      </SheetFooter>
    </SheetContent>
  </Sheet>
</template>