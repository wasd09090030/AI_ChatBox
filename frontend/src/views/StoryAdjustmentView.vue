<script setup lang="ts">
import {
  BookOpen,
  FilePenLine,
  LoaderCircle,
  PencilLine,
  RotateCcw,
  Save,
  Sparkles,
  Wand2,
} from 'lucide-vue-next'
import {
  computed,
  onMounted,
  onUnmounted,
  ref,
  watch,
  type ComponentPublicInstance,
} from 'vue'
import { onBeforeRouteLeave } from 'vue-router'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import StoryLibrarySidebar from '@/components/story/StoryLibrarySidebar.vue'
import type { StoredStory } from '@/components/story/types'
import { useToast } from '@/components/ui/toast'
import { storyAdjustmentApi } from '@/domains/story/api/storyAdjustmentApi'
import { buildStorySessionId } from '@/domains/story/api/storyGenerationApi'
import { storyLibraryApi } from '@/domains/story/api/storyLibraryApi'
import { STORY_ADJUSTMENT_PRESETS } from '@/domains/story/constants/storyAdjustmentPresets'
import { useStoryLibrary } from '@/domains/story/composables/useStoryLibrary'
import { isAppError } from '@/services/errors'
import { useConfigStore } from '@/stores/config'
import { useStorySessionStore } from '@/stores/storySession'

interface StorySelectionState {
  segmentId: string
  start: number
  end: number
  selectedText: string
  rect: {
    top: number
    left: number
    width: number
    height: number
  }
}

interface StoryAdjustmentOperation {
  id: string
  segmentId: string
  previousContent: string
  nextContent: string
  originalText: string
  replacementText: string
  presetKey: string
  customInstruction: string
}

interface StorySegmentDraft {
  segmentId: string
  originalContent: string
  currentContent: string
  operations: StoryAdjustmentOperation[]
}

const configStore = useConfigStore()
const storySessionStore = useStorySessionStore()
const { toast } = useToast()

const {
  worlds,
  worldsLoading,
  selectedWorldId,
  stories,
  storiesLoading,
  currentStory,
  showNewStory,
  newStoryTitle,
  creatingStory,
  createStory,
  deleteStory,
  selectStory,
  syncStory,
} = useStoryLibrary()

const draftSegments = ref<Record<string, StorySegmentDraft>>({})
const undoStack = ref<StoryAdjustmentOperation[]>([])
const selectionState = ref<StorySelectionState | null>(null)
const polishDialogOpen = ref(false)
const selectedPresetKey = ref(STORY_ADJUSTMENT_PRESETS[0]?.key ?? '')
const customInstruction = ref('')
const polishing = ref(false)
const saving = ref(false)
const segmentContentElements = ref<Record<string, HTMLElement | null>>({})
const editingSegmentId = ref<string | null>(null)
const editingContent = ref('')

const isDirty = computed(() => Object.keys(draftSegments.value).length > 0)
const changedSegmentCount = computed(() => Object.keys(draftSegments.value).length)
const selectedPreset = computed(() => (
  STORY_ADJUSTMENT_PRESETS.find((item) => item.key === selectedPresetKey.value) ?? STORY_ADJUSTMENT_PRESETS[0]
))
const floatingActionStyle = computed(() => {
  if (!selectionState.value) return {}
  const top = Math.max(selectionState.value.rect.top - 44, 12)
  const left = Math.min(
    Math.max(selectionState.value.rect.left + selectionState.value.rect.width / 2 - 60, 12),
    window.innerWidth - 132,
  )
  return {
    top: `${top}px`,
    left: `${left}px`,
  }
})

watch(currentStory, () => {
  clearDraftState()
}, { immediate: true })

watch(polishDialogOpen, (open) => {
  if (open || polishing.value) return
  customInstruction.value = ''
  clearSelectionState()
})

function formatTime(ts: string) {
  try {
    return new Date(ts).toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
  } catch {
    return ''
  }
}

function getSegmentContent(segmentId: string, fallbackContent: string) {
  return draftSegments.value[segmentId]?.currentContent ?? fallbackContent
}

function setSegmentContentRef(segmentId: string, el: Element | ComponentPublicInstance | null) {
  if (el instanceof HTMLElement) {
    segmentContentElements.value[segmentId] = el
    return
  }
  if (el && '$el' in el) {
    segmentContentElements.value[segmentId] = el.$el as HTMLElement
    return
  }
  segmentContentElements.value[segmentId] = null
}

function clearSelectionState() {
  selectionState.value = null
}

function clearDraftState() {
  draftSegments.value = {}
  undoStack.value = []
  clearSelectionState()
  editingSegmentId.value = null
  editingContent.value = ''
  polishDialogOpen.value = false
  customInstruction.value = ''
  selectedPresetKey.value = STORY_ADJUSTMENT_PRESETS[0]?.key ?? ''
}

function confirmDiscardChanges() {
  if (!isDirty.value) return true
  return window.confirm('当前有未保存的故事调整，确认放弃这些改动吗？')
}

function handleBeforeUnload(event: BeforeUnloadEvent) {
  if (!isDirty.value) return
  event.preventDefault()
  event.returnValue = ''
}

function handleDocumentMouseDown(event: MouseEvent) {
  if (polishDialogOpen.value) return

  const target = event.target instanceof Element ? event.target : null
  if (!target) return
  if (
    target.closest('[data-story-selection-action]')
    || target.closest('[role="dialog"]')
    || target.closest('[data-segment-id]')
  ) {
    return
  }
  clearSelectionState()
}

function handleWindowScroll() {
  clearSelectionState()
}

onMounted(() => {
  window.addEventListener('beforeunload', handleBeforeUnload)
  document.addEventListener('mousedown', handleDocumentMouseDown)
  window.addEventListener('scroll', handleWindowScroll, true)
})

onUnmounted(() => {
  window.removeEventListener('beforeunload', handleBeforeUnload)
  document.removeEventListener('mousedown', handleDocumentMouseDown)
  window.removeEventListener('scroll', handleWindowScroll, true)
})

onBeforeRouteLeave(() => confirmDiscardChanges())

function findSegmentRoot(node: Node): HTMLElement | null {
  const element = node instanceof HTMLElement ? node : node.parentElement
  return element?.closest('[data-segment-id]') as HTMLElement | null
}

function computeTextOffset(root: HTMLElement, container: Node, offset: number) {
  const range = document.createRange()
  range.selectNodeContents(root)
  range.setEnd(container, offset)
  return range.toString().length
}

function handleContentMouseUp(segmentId: string) {
  window.requestAnimationFrame(() => {
    const selection = window.getSelection()
    if (!selection || selection.rangeCount === 0 || selection.isCollapsed) {
      clearSelectionState()
      return
    }

    const range = selection.getRangeAt(0)
    const startRoot = findSegmentRoot(range.startContainer)
    const endRoot = findSegmentRoot(range.endContainer)
    if (!startRoot || !endRoot || startRoot !== endRoot || startRoot.dataset.segmentId !== segmentId) {
      clearSelectionState()
      toast({ title: '暂不支持', description: '当前版本仅支持单段内容内的局部润色。' })
      return
    }

    const story = currentStory.value
    const segment = story?.segments.find((item) => item.id === segmentId)
    const content = segment ? getSegmentContent(segmentId, segment.content) : (startRoot.textContent ?? '')
    const start = computeTextOffset(startRoot, range.startContainer, range.startOffset)
    const end = computeTextOffset(startRoot, range.endContainer, range.endOffset)
    if (end <= start) {
      clearSelectionState()
      return
    }

    const selectedText = content.slice(start, end)
    if (!selectedText.trim()) {
      clearSelectionState()
      return
    }

    const rect = range.getBoundingClientRect()
    selectionState.value = {
      segmentId,
      start,
      end,
      selectedText,
      rect: {
        top: rect.top,
        left: rect.left,
        width: rect.width,
        height: rect.height,
      },
    }
  })
}

function openPolishDialog() {
  if (!selectionState.value) return
  polishDialogOpen.value = true
}

function openManualEdit(segmentId: string) {
  const story = currentStory.value
  const segment = story?.segments.find((item) => item.id === segmentId)
  if (!segment) return

  if (
    editingSegmentId.value
    && editingSegmentId.value !== segmentId
    && editingContent.value !== getSegmentContent(editingSegmentId.value, story?.segments.find((item) => item.id === editingSegmentId.value)?.content ?? '')
  ) {
    const confirmed = window.confirm('当前段落仍有未应用的手动修改内容，确认切换到其他段落吗？')
    if (!confirmed) return
  }

  clearSelectionState()
  editingSegmentId.value = segmentId
  editingContent.value = getSegmentContent(segmentId, segment.content)
}

function cancelManualEdit() {
  editingSegmentId.value = null
  editingContent.value = ''
}

function closePolishDialog() {
  polishDialogOpen.value = false
  customInstruction.value = ''
  clearSelectionState()
}

function applyDraftOperation(operation: StoryAdjustmentOperation) {
  const sourceStory = currentStory.value
  if (!sourceStory) return
  const sourceSegment = sourceStory.segments.find((item) => item.id === operation.segmentId)
  if (!sourceSegment) return

  const existingDraft = draftSegments.value[operation.segmentId]
  const originalContent = existingDraft?.originalContent ?? sourceSegment.content
  const operations = [...(existingDraft?.operations ?? []), operation]

  draftSegments.value = {
    ...draftSegments.value,
    [operation.segmentId]: {
      segmentId: operation.segmentId,
      originalContent,
      currentContent: operation.nextContent,
      operations,
    },
  }
  undoStack.value.push(operation)
}

function applyManualEdit() {
  const story = currentStory.value
  const segmentId = editingSegmentId.value
  if (!story || !segmentId) return

  const segment = story.segments.find((item) => item.id === segmentId)
  if (!segment) return

  const currentContent = getSegmentContent(segmentId, segment.content)
  const nextContent = editingContent.value

  if (nextContent === currentContent) {
    cancelManualEdit()
    return
  }

  applyDraftOperation({
    id: `adjust-manual-${Date.now()}`,
    segmentId,
    previousContent: currentContent,
    nextContent,
    originalText: currentContent,
    replacementText: nextContent,
    presetKey: 'manual_edit',
    customInstruction: '手动整段修改',
  })

  toast({
    title: '手动修改已加入草稿',
    description: '当前段落的新文本已进入草稿区，保存后才会正式写回故事。',
  })
  cancelManualEdit()
}

async function applyPolish() {
  const story = currentStory.value
  const selection = selectionState.value
  const preset = selectedPreset.value
  if (!story || !selection || !preset) return

  const segment = story.segments.find((item) => item.id === selection.segmentId)
  if (!segment) return

  const currentContent = getSegmentContent(selection.segmentId, segment.content)
  const beforeContext = currentContent.slice(Math.max(0, selection.start - 160), selection.start)
  const afterContext = currentContent.slice(selection.end, Math.min(currentContent.length, selection.end + 160))
  const storyAdjustmentModel = configStore.getResolvedSceneModel('story_adjustment')

  polishing.value = true
  try {
    const response = await storyAdjustmentApi.polish({
      story_id: story.id,
      session_id: buildStorySessionId(story.id),
      segment_id: selection.segmentId,
      selected_text: selection.selectedText,
      before_context: beforeContext,
      after_context: afterContext,
      preset_key: preset.key,
      preset_instruction: preset.instruction,
      custom_instruction: customInstruction.value.trim() || undefined,
      world_id: selectedWorldId.value || undefined,
      model: storyAdjustmentModel.model,
      provider: storyAdjustmentModel.provider,
      base_url: storyAdjustmentModel.base_url,
      temperature: configStore.config.temperature,
    })

    const nextContent = (
      currentContent.slice(0, selection.start)
      + response.polished_text
      + currentContent.slice(selection.end)
    )

    applyDraftOperation({
      id: `adjust-${Date.now()}`,
      segmentId: selection.segmentId,
      previousContent: currentContent,
      nextContent,
      originalText: selection.selectedText,
      replacementText: response.polished_text,
      presetKey: preset.key,
      customInstruction: customInstruction.value.trim(),
    })

    toast({
      title: '润色完成',
      description: `已应用「${preset.label}」方案，你可以继续调整或保存。`,
    })
    closePolishDialog()
  } catch (error: unknown) {
    toast({
      title: '润色失败',
      description: error instanceof Error ? error.message : '无法完成当前润色请求',
      variant: 'destructive',
    })
  } finally {
    polishing.value = false
  }
}

function undoLastChange() {
  const lastOperation = undoStack.value[undoStack.value.length - 1]
  if (!lastOperation) return

  const draft = draftSegments.value[lastOperation.segmentId]
  if (!draft) {
    undoStack.value = undoStack.value.slice(0, -1)
    return
  }

  const nextUndoStack = undoStack.value.slice(0, -1)
  const remainingOperations = draft.operations.slice(0, -1)
  const restoredContent = lastOperation.previousContent

  if (!remainingOperations.length && restoredContent === draft.originalContent) {
    const nextDraftSegments = { ...draftSegments.value }
    delete nextDraftSegments[lastOperation.segmentId]
    draftSegments.value = nextDraftSegments
  } else {
    draftSegments.value = {
      ...draftSegments.value,
      [lastOperation.segmentId]: {
        ...draft,
        currentContent: restoredContent,
        operations: remainingOperations,
      },
    }
  }

  undoStack.value = nextUndoStack
  clearSelectionState()
  toast({ title: '已撤销', description: '最近一次未保存的润色改动已回退。' })
}

async function saveChanges() {
  const story = currentStory.value
  if (!story || !isDirty.value || saving.value) return

  const liveSegmentIds = new Set(story.segments.map((item) => item.id))
  const staleDraftSegmentIds = Object.values(draftSegments.value)
    .map((item) => item.segmentId)
    .filter((segmentId) => !liveSegmentIds.has(segmentId))

  if (staleDraftSegmentIds.length) {
    const nextDraftSegments = { ...draftSegments.value }
    for (const segmentId of staleDraftSegmentIds) {
      delete nextDraftSegments[segmentId]
    }
    draftSegments.value = nextDraftSegments
    undoStack.value = undoStack.value.filter((item) => liveSegmentIds.has(item.segmentId))
    if (editingSegmentId.value && !liveSegmentIds.has(editingSegmentId.value)) {
      cancelManualEdit()
    }
    clearSelectionState()
    toast({
      title: '草稿已刷新',
      description: '部分段落已被其他操作改动或删除，对应草稿已移除，请确认后再保存。',
    })
  }

  const updates = Object.values(draftSegments.value)
    .filter((item) => liveSegmentIds.has(item.segmentId))
    .filter((item) => item.currentContent !== item.originalContent)
    .map((item) => ({
      segment_id: item.segmentId,
      content: item.currentContent,
    }))
  if (!updates.length) {
    toast({
      title: '没有可保存的变更',
      description: '当前草稿与正式故事内容一致，或对应段落已失效。',
    })
    return
  }

  saving.value = true
  const sessionId = buildStorySessionId(story.id)
  try {
    const response = await storyLibraryApi.commitAdjustments(story.id, {
      session_id: sessionId,
      updates,
    })
    syncStory(response.story)
    if (response.memory_updates.length) {
      storySessionStore.appendMemoryEvents(
        response.session_id,
        response.story.title,
        response.story.world_id,
        response.memory_updates,
      )
    }

    if (
      response.rebuild_summary_reset
      || response.memory_updates.some((event) => event.memory_layer === 'semantic' && event.action === 'reset')
    ) {
      storySessionStore.removeSummary(response.session_id)
    }
    clearDraftState()

    const failedMemoryUpdates = response.memory_updates.filter((event) => event.status === 'failed')
    if (response.warnings.length) {
      toast({
        title: '保存完成，但有警告',
        description: response.warnings.join('；'),
      })
    } else if (failedMemoryUpdates.length) {
      toast({
        title: '调整已保存，但记忆重建不完整',
        description: failedMemoryUpdates.map((event) => event.title).join('；'),
      })
    } else {
      toast({
        title: '调整已保存',
        description: response.rebuild_history_reindexed
          ? '故事正文、历史索引和记忆事件都已同步更新。'
          : '故事正文已保存，记忆事件已记录。',
      })
    }
  } catch (error: unknown) {
    toast({
      title: '保存失败',
      description: isAppError(error)
        ? error.message
        : error instanceof Error
          ? error.message
          : '无法提交当前故事调整',
      variant: 'destructive',
    })
  } finally {
    saving.value = false
  }
}

function handleWorldChange(worldId: string) {
  if (worldId === selectedWorldId.value) return
  if (!confirmDiscardChanges()) return
  clearDraftState()
  selectedWorldId.value = worldId
}

function handleSelectStory(story: StoredStory) {
  if (currentStory.value?.id === story.id) return
  if (!confirmDiscardChanges()) return
  clearDraftState()
  selectStory(story)
}

async function handleDeleteStory(story: StoredStory) {
  if (currentStory.value?.id === story.id && !confirmDiscardChanges()) return
  await deleteStory(story)
}

function handleCreateStory() {
  if (!confirmDiscardChanges()) return
  showNewStory.value = true
}
</script>

<template>
  <div class="flex h-full bg-background">
    <StoryLibrarySidebar
      :selected-world-id="selectedWorldId"
      :worlds="worlds ?? []"
      :worlds-loading="worldsLoading"
      :stories="stories"
      :stories-loading="storiesLoading"
      :current-story-id="currentStory?.id ?? null"
      @update:selected-world-id="handleWorldChange"
      @create-story="handleCreateStory"
      @select-story="handleSelectStory"
      @delete-story="handleDeleteStory"
    />

    <div class="flex min-w-0 flex-1 flex-col">
      <header class="flex h-12 items-center justify-between border-b border-border px-4 shrink-0">
        <div class="flex min-w-0 items-center gap-2">
          <FilePenLine class="h-4 w-4 shrink-0 text-muted-foreground" />
          <span v-if="currentStory" class="truncate text-sm font-medium">{{ currentStory.title }}</span>
          <span v-else class="text-sm text-muted-foreground">故事调整</span>
          <Badge v-if="currentStory" variant="secondary" class="text-[11px] shrink-0">
            {{ currentStory.segments.length }} 段
          </Badge>
          <Badge v-if="isDirty" class="bg-amber-100 text-amber-900 hover:bg-amber-100">
            {{ changedSegmentCount }} 处未保存
          </Badge>
        </div>

        <div class="flex items-center gap-2">
          <Button
            size="sm"
            variant="ghost"
            class="h-8 gap-1.5 text-xs"
            :disabled="!undoStack.length || saving"
            @click="undoLastChange"
          >
            <RotateCcw class="h-3.5 w-3.5" />
            撤销本地改动
          </Button>
          <Button
            size="sm"
            class="h-8 gap-1.5 text-xs"
            :disabled="!isDirty || saving"
            @click="saveChanges"
          >
            <LoaderCircle v-if="saving" class="h-3.5 w-3.5 animate-spin" />
            <Save v-else class="h-3.5 w-3.5" />
            保存到故事
          </Button>
        </div>
      </header>

      <div class="min-h-0 flex-1 overflow-y-auto px-6 py-4">
        <div v-if="!currentStory" class="flex h-full flex-col items-center justify-center py-20 text-center text-muted-foreground">
          <BookOpen class="mb-4 h-14 w-14 opacity-20" />
          <p class="text-base font-medium">选择一个故事开始调整</p>
          <p class="mt-1 text-sm opacity-70">从左侧世界和故事列表中选择目标故事</p>
        </div>

        <div v-else-if="!currentStory.segments.length" class="flex flex-col items-center justify-center py-20 text-muted-foreground">
          <Sparkles class="mb-3 h-10 w-10 opacity-20" />
          <p class="text-sm">这个故事还没有 AI 输出内容，暂时没有可调整的段落。</p>
        </div>

        <div v-else class="mx-auto w-full max-w-4xl">
          <div class="relative overflow-hidden rounded-[28px] border border-border/60 bg-card/80 px-6 py-7 shadow-sm backdrop-blur sm:px-10 sm:py-10">
            <div class="pointer-events-none absolute inset-x-8 top-0 h-px bg-gradient-to-r from-transparent via-primary/35 to-transparent" />

            <div class="mb-8 flex flex-wrap items-center gap-3 border-b border-border/60 pb-4">
              <span class="text-[16px] font-medium uppercase tracking-[0.28em] text-muted-foreground">
                故事调整
              </span>
              <span class="text-sm text-muted-foreground">
                选中局部内容可用 AI 润色，也可以按段手动修改后统一保存
              </span>
            </div>

            <article class="space-y-8 text-[15px] leading-8 text-foreground sm:text-base sm:leading-8">
              <section
                v-for="(seg, index) in currentStory.segments"
                :key="seg.id"
                class="group relative"
                :class="index === 0 ? '' : 'border-t border-border/45 pt-8'"
              >
                <div class="mb-3 flex flex-wrap items-center justify-between gap-3">
                  <p
                    class="min-w-0 flex-1 truncate border-l-2 border-primary/35 pl-3 text-xs tracking-[0.16em] text-muted-foreground/90"
                    :title="seg.prompt"
                  >
                    {{ seg.prompt }}
                  </p>

                  <div class="flex items-center gap-2">
                    <Badge
                      v-if="draftSegments[seg.id]"
                      variant="secondary"
                      class="bg-cyan-100 text-cyan-900 hover:bg-cyan-100"
                    >
                      草稿中
                    </Badge>
                    <Button
                      size="sm"
                      variant="ghost"
                      class="h-7 gap-1.5 px-2 text-[11px] text-muted-foreground hover:text-foreground"
                      :disabled="saving || polishing"
                      @click="openManualEdit(seg.id)"
                    >
                      <PencilLine class="h-3.5 w-3.5" />
                      {{ editingSegmentId === seg.id ? '编辑中' : '手动修改' }}
                    </Button>
                    <span class="shrink-0 text-[11px] text-muted-foreground/80">
                      {{ formatTime(seg.timestamp) }}
                    </span>
                  </div>
                </div>

                <div class="pl-4 sm:pl-5">
                  <div v-if="editingSegmentId === seg.id" class="space-y-3">
                    <Textarea
                      v-model="editingContent"
                      class="min-h-[220px] resize-y border-border/70 bg-background/70 text-[15px] leading-7"
                      placeholder="直接修改这一段的大模型输出内容"
                    />
                    <div class="flex items-center justify-end gap-2">
                      <Button size="sm" variant="ghost" :disabled="saving" @click="cancelManualEdit">
                        取消
                      </Button>
                      <Button size="sm" :disabled="saving" @click="applyManualEdit">
                        应用到草稿
                      </Button>
                    </div>
                  </div>
                  <div
                    v-else
                    :ref="(el) => setSegmentContentRef(seg.id, el)"
                    :data-segment-id="seg.id"
                    class="select-text whitespace-pre-wrap text-[15px] leading-8 text-foreground/95 transition-colors duration-200 group-hover:text-foreground sm:text-base"
                    @mouseup="handleContentMouseUp(seg.id)"
                  >
                    {{ getSegmentContent(seg.id, seg.content) }}
                  </div>
                </div>
              </section>
            </article>
          </div>
        </div>
      </div>

      <div
        v-if="selectionState"
        data-story-selection-action
        class="fixed z-40"
        :style="floatingActionStyle"
      >
        <Button size="sm" class="h-9 gap-1.5 rounded-full px-3 shadow-lg" @click="openPolishDialog">
          <Wand2 class="h-3.5 w-3.5" />
          AI 润色
        </Button>
      </div>
    </div>

    <Dialog v-model:open="showNewStory">
      <DialogContent class="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>新建故事</DialogTitle>
          <DialogDescription>故事调整页也可以直接创建新故事，创建后可继续回到创作页生成内容。</DialogDescription>
        </DialogHeader>
        <div class="space-y-2">
          <Label for="story-adjustment-new-title">故事标题</Label>
          <Input
            id="story-adjustment-new-title"
            v-model="newStoryTitle"
            placeholder="输入故事标题"
            @keydown.enter.prevent="createStory"
          />
        </div>
        <DialogFooter>
          <Button variant="ghost" @click="showNewStory = false">取消</Button>
          <Button :disabled="creatingStory || !newStoryTitle.trim()" @click="createStory">
            <LoaderCircle v-if="creatingStory" class="mr-1 h-4 w-4 animate-spin" />
            创建
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>

    <Dialog v-model:open="polishDialogOpen">
      <DialogContent class="sm:max-w-xl">
        <DialogHeader>
          <DialogTitle>AI 润色选中文本</DialogTitle>
          <DialogDescription>先选择一个预设方案，再按需要补充自定义要求。当前版本只会改写选中部分，不会自动改动整段。</DialogDescription>
        </DialogHeader>

        <div class="space-y-4">
          <div class="space-y-2">
            <Label>选中文本</Label>
            <div class="max-h-40 overflow-y-auto whitespace-pre-wrap rounded-lg border border-border/70 bg-muted/30 px-3 py-2 text-sm leading-6">
              {{ selectionState?.selectedText }}
            </div>
          </div>

          <div class="space-y-2">
            <Label>预设润色方案</Label>
            <Select v-model="selectedPresetKey">
              <SelectTrigger>
                <SelectValue placeholder="选择预设方案" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem
                  v-for="preset in STORY_ADJUSTMENT_PRESETS"
                  :key="preset.key"
                  :value="preset.key"
                >
                  {{ preset.label }}
                </SelectItem>
              </SelectContent>
            </Select>
            <p class="text-xs text-muted-foreground">
              {{ selectedPreset?.description }}
            </p>
          </div>

          <div class="space-y-2">
            <Label for="story-adjustment-custom-instruction">自定义补充要求</Label>
            <Textarea
              id="story-adjustment-custom-instruction"
              v-model="customInstruction"
              class="min-h-[96px]"
              placeholder="可选。例如：语气更冷一点，但不要变成诗化表达。"
            />
          </div>
        </div>

        <DialogFooter>
          <Button variant="ghost" :disabled="polishing" @click="closePolishDialog">取消</Button>
          <Button :disabled="polishing || !selectionState" @click="applyPolish">
            <LoaderCircle v-if="polishing" class="mr-1 h-4 w-4 animate-spin" />
            <Wand2 v-else class="mr-1 h-4 w-4" />
            应用润色
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  </div>
</template>
