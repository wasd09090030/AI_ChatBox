<script setup lang="ts">
import { ref, computed, watch, nextTick, onActivated } from 'vue'
import {
  Send, Square, Sparkles, ListOrdered, ChevronRight, Wand2, LoaderCircle, CircleHelp, PenLine, Route,
} from 'lucide-vue-next'
import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'
import { Badge } from '@/components/ui/badge'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from '@/components/ui/dialog'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import StoryLibrarySidebar from '@/components/story/StoryLibrarySidebar.vue'
import StoryConversationList from '@/components/story/StoryConversationList.vue'
import StoryControlDrawer from '@/components/story/StoryControlDrawer.vue'
import StoryInputSuggestions from '@/components/story/StoryInputSuggestions.vue'
import StoryMemorySidebar from '@/components/story/StoryMemorySidebar.vue'
import StoryPromptComposerSheet from '@/components/story/StoryPromptComposerSheet.vue'
import StoryScriptSidebar from '@/components/story/StoryScriptSidebar.vue'
import type { StoryMode } from '@/components/story/types'
import { STORY_PROMPT_FOCUS_TEMPLATES } from '@/config/prompts'
import {
  getStoryMemoryEntitySnapshot,
  getStoryMemoryEntityUpdates,
  getStoryMemorySummarySnapshot,
  getStoryMemoryTimelineEvents,
  getStoryMemoryWorldUpdate,
} from '@/domains/story/storyMemoryPayload'
import { usePersonasQuery } from '@/domains/roleplay/queries/useRoleplayQueries'
import { useConfigStore } from '@/stores/config'
import { useStorySessionStore } from '@/stores/storySession'
import {
  useStoryDraftStateStore,
  type RouteStoryDraftState,
  type SharedStoryDraftState,
} from '@/stores/storyDraftState'
import { useLorebookEntriesQuery } from '@/domains/lorebook/queries/useLorebookQueries'
import { useScriptDesignsQuery } from '@/domains/story/queries/useScriptDesignQueries'
import { useToast } from '@/components/ui/toast'
import { cn } from '@/lib/utils'
import { useStoryLibrary } from '@/domains/story/composables/useStoryLibrary'
import { useStoryPromptComposer } from '@/domains/story/composables/useStoryPromptComposer'
import { useStoryGeneration } from '@/domains/story/composables/useStoryGeneration'
import { storyLibraryApi } from '@/domains/story/api/storyLibraryApi'
import type { StoryRuntimeState } from '@/domains/story/api/storyLibraryApi'
import type { LorebookEntry } from '@/services/lorebookService'
import type { StoredStory } from '@/components/story/types'

const props = withDefaults(defineProps<{
  pageMode?: 'improv' | 'scripted'
}>(), {
  pageMode: 'improv',
})

const configStore = useConfigStore()
const storySessionStore = useStorySessionStore()
const storyDraftStore = useStoryDraftStateStore()
const { toast } = useToast()

// ── Remote data ──────────────────────────────────────────────────────────────
const { data: personas, isLoading: personasLoading } = usePersonasQuery()

// ── Story / session state ────────────────────────────────────────────────────
const {
  worlds,
  worldsLoading,
  selectedWorldId,
  stories,
  storiesLoading,
  currentStory,
  v2SessionId,
  showNewStory,
  newStoryTitle,
  creatingStory,
  ensureV2Session,
  createStory,
  deleteStory,
  selectStory,
} = useStoryLibrary()
const { data: lorebookEntriesData, isLoading: lorebookEntriesLoading } = useLorebookEntriesQuery(selectedWorldId)
const { data: scriptDesignsData } = useScriptDesignsQuery(selectedWorldId)

// ── Generation state ─────────────────────────────────────────────────────────
const scrollRef = ref<HTMLElement | null>(null)
const textareaRef = ref<HTMLTextAreaElement | null>(null)
const shouldStickToBottom = ref(true)
const currentStoryId = computed(() => currentStory.value?.id ?? null)

function sharedDraftRef<K extends keyof SharedStoryDraftState>(
  key: K,
  fallback: SharedStoryDraftState[K],
) {
  return computed<SharedStoryDraftState[K]>({
    get: () => {
      const storyId = currentStoryId.value
      if (!storyId) return fallback
      return storyDraftStore.ensureSharedDraft(storyId)[key]
    },
    set: (value) => {
      const storyId = currentStoryId.value
      if (!storyId) return
      storyDraftStore.ensureSharedDraft(storyId)[key] = value
    },
  })
}

function routeDraftRef<K extends keyof RouteStoryDraftState>(
  key: K,
  fallback: RouteStoryDraftState[K],
) {
  return computed<RouteStoryDraftState[K]>({
    get: () => {
      const storyId = currentStoryId.value
      if (!storyId) return fallback
      return storyDraftStore.ensureRouteDraft(storyId, props.pageMode)[key]
    },
    set: (value) => {
      const storyId = currentStoryId.value
      if (!storyId) return
      storyDraftStore.ensureRouteDraft(storyId, props.pageMode)[key] = value
    },
  })
}

// ── SillyTavern controls ─────────────────────────────────────────────────────
const storyMode = routeDraftRef('storyMode', 'choices' as StoryMode)
const authorsNote = routeDraftRef('authorsNote', '')
const instruction = routeDraftRef('instruction', '')
const showControlPanel = ref(false)
const showControlDrawer = ref(false)
const showScriptSidebar = ref(false)
const selectedPersonaId = sharedDraftRef('selectedPersonaId', null)
const selectedScriptDesignId = ref<string | null>(null)
const selectedScriptStageId = ref<string | null>(null)
const selectedScriptEventId = ref<string | null>(null)
const followScriptDesign = ref(false)
const creationMode = ref<'improv' | 'scripted'>(props.pageMode)
const progressIntent = routeDraftRef('progressIntent', 'hold')
const runtimeStateId = ref<string | null>(null)
const selectedPrincipalCharacterId = sharedDraftRef('selectedPrincipalCharacterId', null)
const dialogueMode = sharedDraftRef('dialogueMode', 'auto')
const dialogueTarget = sharedDraftRef('dialogueTarget', '')
const dialogueIntent = sharedDraftRef('dialogueIntent', '')
const dialogueStyleHint = sharedDraftRef('dialogueStyleHint', '')
const userInputDraft = routeDraftRef('userInput', '')
const selectedContextEntryIdsDraft = sharedDraftRef('selectedContextEntryIds', [])
const selectedFocusTemplateIdDraft = sharedDraftRef('selectedFocusTemplateId', '')

// ── Context / memory sidebar ─────────────────────────────────────────────────
const showSidebar = ref(false)
const currentStoryMemoryPayload = computed(() => {
  const sessionId = v2SessionId.value || (currentStory.value ? `story-${currentStory.value.id}-v2` : '')
  if (!sessionId) return null
  return storySessionStore.getStoryMemorySession(sessionId)?.storyMemory ?? null
})
const currentSummarySnapshot = computed(() => {
  const sessionId = v2SessionId.value || (currentStory.value ? `story-${currentStory.value.id}-v2` : '')
  const summaryFromMemory = getStoryMemorySummarySnapshot(currentStoryMemoryPayload.value)
  if (summaryFromMemory) return summaryFromMemory
  return (sessionId ? storySessionStore.getSummarySnapshot(sessionId) : null) ?? lastSummary.value
})
const currentMemoryUpdates = computed(() => {
  const sessionId = v2SessionId.value || (currentStory.value ? `story-${currentStory.value.id}-v2` : '')
  const storyMemoryUpdates = getStoryMemoryTimelineEvents(currentStoryMemoryPayload.value, 20)
  if (storyMemoryUpdates.length) return storyMemoryUpdates
  if (!sessionId) return lastMemoryUpdates.value
  return storySessionStore.getSessionMemoryEvents(sessionId, 20).map((item) => ({
    event_id: item.eventId,
    session_id: item.sessionId,
    operation_id: item.operationId,
    sequence: item.sequence,
    display_kind: item.displayKind,
    memory_layer: item.memoryLayer,
    action: item.action,
    source: item.source,
    source_turn: item.sourceTurn,
    memory_key: item.memoryKey,
    title: item.title,
    reason: item.reason,
    before: item.before,
    after: item.after,
    status: item.status,
    committed_at: item.committedAt,
  }))
})
const currentEntityStateSnapshot = computed(() => {
  const sessionId = v2SessionId.value || (currentStory.value ? `story-${currentStory.value.id}-v2` : '')
  const storyMemorySnapshot = getStoryMemoryEntitySnapshot(currentStoryMemoryPayload.value)
  if (storyMemorySnapshot) return storyMemorySnapshot
  if (!sessionId) return null
  return storySessionStore.getEntityStateSnapshot(sessionId)
})
const currentEntityStateUpdates = computed(() => {
  const sessionId = v2SessionId.value || (currentStory.value ? `story-${currentStory.value.id}-v2` : '')
  const storyMemoryUpdates = getStoryMemoryEntityUpdates(currentStoryMemoryPayload.value, 12)
  if (storyMemoryUpdates.length) return storyMemoryUpdates
  if (!sessionId) return []
  return storySessionStore.getSessionEntityStateUpdates(sessionId, 12)
})
const currentWorldUpdate = computed(() => {
  const sessionId = v2SessionId.value || (currentStory.value ? `story-${currentStory.value.id}-v2` : '')
  const storyMemoryWorldUpdate = getStoryMemoryWorldUpdate(currentStoryMemoryPayload.value)
  if (storyMemoryWorldUpdate) return storyMemoryWorldUpdate
  if (!sessionId) return null
  return storySessionStore.getSessionWorldUpdate(sessionId)?.payload ?? null
})

// ── Helpers ──────────────────────────────────────────────────────────────────
const modeLabels: Record<StoryMode, string> = {
  narrative: '叙事',
  choices:   '选项',
  instruction: '指令',
}

const pageModeLabel = computed(() => (
  props.pageMode === 'scripted' ? '严格剧本创作' : '渐进式创作'
))
const isScriptedPage = computed(() => props.pageMode === 'scripted')
const pageModeDescription = computed(() => (
  props.pageMode === 'scripted'
    ? '结构驱动的主线创作页面，剧情推进以后端运行态为准。'
    : '高自由度的即兴创作页面，允许 Prompt 和上下文自然扩展故事。'
))
const alternateRoute = computed(() => (
  props.pageMode === 'scripted' ? '/story/improv' : '/story/scripted'
))
const alternateRouteLabel = computed(() => (
  props.pageMode === 'scripted' ? '切换到渐进式创作' : '切换到严格剧本创作'
))
const promptInputDomId = computed(() => (
  isScriptedPage.value ? 'story-scripted-micro-adjust-input' : 'story-improv-prompt-input'
))
const promptInputName = computed(() => (
  isScriptedPage.value ? 'scripted_micro_adjust_note' : 'improv_prompt'
))
const controlDrawerTitle = computed(() => (
  isScriptedPage.value ? '角色控制' : '创作控制'
))
const promptComposerButtonLabel = computed(() => (
  isScriptedPage.value ? '本轮微调' : 'Prompt 编排'
))
const inputAssistTitle = computed(() => (
  isScriptedPage.value ? '本轮微调说明' : 'AI 增强 Prompt'
))
const inputAssistDescription = computed(() => (
  isScriptedPage.value
    ? '这里只优化本轮镜头、节奏和描写重点，不负责决定主线推进。'
    : '点击按钮生成增强版本，再决定是否填入输入框'
))
const inputAssistButtonLabel = computed(() => (
  isScriptedPage.value ? '优化微调说明' : '增强 Prompt'
))
const inputPreviewOriginalLabel = computed(() => (
  isScriptedPage.value ? '原始微调说明' : '原始 Prompt'
))
const inputPreviewEnhancedLabel = computed(() => (
  isScriptedPage.value ? '优化后微调说明' : '增强后 Prompt'
))
const templatePreviewTitle = computed(() => (
  isScriptedPage.value ? '微调模板预览' : '指令模板预览'
))
const inputPlaceholder = computed(() => (
  isScriptedPage.value
    ? '输入本轮微调说明，例如强调当前事件的冲突、节奏或对白重点… (Shift+Enter 换行)'
    : '输入提示词继续故事… (Shift+Enter 换行)'
))
const scriptedMicroAdjustHelp = [
  '可以写：本轮镜头重点、情绪力度、对白密度、节奏快慢。',
  '不要写：直接切换主线、跳过阶段、强行完成未达条件的事件。',
  '推荐写法：强调当前事件里的冲突、悬念、人物互动或信息揭示方式。',
]

const promptFocusTemplates = STORY_PROMPT_FOCUS_TEMPLATES
const NONE_OPTION_VALUE = '__story-persona-none__'

const lorebookEntries = computed(() => lorebookEntriesData.value?.entries ?? [])
const scriptDesigns = computed(() => scriptDesignsData.value ?? [])
const selectedScriptDesign = computed(() => (
  scriptDesigns.value.find((item) => item.id === selectedScriptDesignId.value) ?? null
))
const scriptStages = computed(() => selectedScriptDesign.value?.stage_outlines ?? [])
const activeScriptStage = computed(() => (
  scriptStages.value.find((item) => item.id === selectedScriptStageId.value) ?? null
))
const scriptEvents = computed(() => {
  const design = selectedScriptDesign.value
  if (!design) return []
  if (!selectedScriptStageId.value) return design.event_nodes
  return design.event_nodes.filter((item) => item.stage_id === selectedScriptStageId.value)
})
const activeScriptEvent = computed(() => (
  (selectedScriptDesign.value?.event_nodes ?? []).find((item) => item.id === selectedScriptEventId.value) ?? null
))
const progressUpdating = ref(false)
const lorebookCharacterEntries = computed(() => lorebookEntries.value.filter((entry) => entry.type === 'character'))
const selectedPrincipalCharacter = computed<LorebookEntry | null>(() => (
  lorebookCharacterEntries.value.find((entry) => entry.id === selectedPrincipalCharacterId.value) ?? null
))
const {
  showPromptComposer,
  selectedContextEntryIds,
  draftContextEntryIds,
  draftFocusTemplateId,
  currentComposerTab,
  composerSearchQuery,
  filteredCharacterEntries,
  filteredLocationEntries,
  filteredEventEntries,
  composerPreviewEntry,
  selectedContextEntries,
  activeFocusTemplate,
  promptDrawerBadgeText,
  resetComposerState,
  openPromptComposer,
  openComposerEntry,
  toggleDraftContextEntry,
  isDraftEntrySelected,
  applyPromptComposerSelection,
  clearPromptComposerSelection,
  removeSelectedContextEntry,
  clearSelectedFocusTemplate,
} = useStoryPromptComposer({
  lorebookEntries,
  promptFocusTemplates,
  selectedContextEntryIds: selectedContextEntryIdsDraft,
  selectedFocusTemplateId: selectedFocusTemplateIdDraft,
})
const controlDrawerBadgeText = computed(() => (
  isScriptedPage.value ? '角色' : modeLabels[storyMode.value]
))
const selectedPersona = computed(() => (
  personas.value?.find((item) => item.id === selectedPersonaId.value) ?? null
))
const selectedPersonaSummaryText = computed(() => selectedPersona.value?.name ?? '默认：你自己')
const selectedPersonaSelectValue = computed({
  get: () => selectedPersonaId.value ?? NONE_OPTION_VALUE,
  set: (value: string) => {
    selectedPersonaId.value = value === NONE_OPTION_VALUE ? null : value
  },
})

watch(() => props.pageMode, (mode) => {
  creationMode.value = mode
  if (mode === 'scripted') {
    storyMode.value = 'narrative'
    authorsNote.value = ''
    instruction.value = ''
    showControlPanel.value = false
    followScriptDesign.value = true
  } else {
    progressIntent.value = 'hold'
  }
}, { immediate: true })

async function hydrateRuntimeStateFromStory(story: StoredStory | null) {
  if (!story) return

  const metadata = story.metadata ?? {}
  const shouldLoadRuntime = Boolean(
    story && (
      props.pageMode === 'scripted'
      || runtimeStateId.value
      || selectedScriptDesignId.value
      || metadata.creation_mode === 'scripted'
    ),
  )

  if (!shouldLoadRuntime) return

  try {
    const runtimeState = await storyLibraryApi.getRuntime(story.id)
    runtimeStateId.value = runtimeState.id
    selectedScriptDesignId.value = runtimeState.script_design_id
    selectedScriptStageId.value = runtimeState.current_stage_id ?? selectedScriptStageId.value
    selectedScriptEventId.value = runtimeState.current_event_id ?? selectedScriptEventId.value
    if (props.pageMode === 'scripted') {
      followScriptDesign.value = true
    } else {
      followScriptDesign.value = runtimeState.creation_mode === 'scripted'
    }
    story.metadata.runtime_state_id = runtimeState.id
    story.metadata.creation_mode = runtimeState.creation_mode
    story.metadata.script_design_id = runtimeState.script_design_id
    if (runtimeState.current_stage_id) story.metadata.active_stage_id = runtimeState.current_stage_id
    if (runtimeState.current_event_id) story.metadata.active_event_id = runtimeState.current_event_id
  } catch {
    // Ignore missing runtime state; old stories can still run via metadata fallback.
  }
}

async function refreshEntityStateFromStory(story: StoredStory | null) {
  if (!story) return
  try {
    const snapshot = await storyLibraryApi.getEntityState(story.id)
    storySessionStore.updateEntityStateSnapshot(snapshot)
  } catch {
    // Ignore absent state for legacy stories or sessions that have not been rebuilt yet.
  }
}

function isNearBottom() {
  if (!scrollRef.value) return true
  const distance = scrollRef.value.scrollHeight - scrollRef.value.scrollTop - scrollRef.value.clientHeight
  return distance <= 80
}

function handleStoryScroll() {
  shouldStickToBottom.value = isNearBottom()
}

function scrollToBottom(options?: { force?: boolean }) {
  if (!scrollRef.value) return
  if (!options?.force && !shouldStickToBottom.value) return
  scrollRef.value.scrollTop = scrollRef.value.scrollHeight
  shouldStickToBottom.value = true
}
const {
  userInput,
  generating,
  lastChoices,
  lastContexts,
  lastSummary,
  lastMemoryUpdates,
  lastSummaryDiff,
  previewSourceText,
  enhancedInputPreview,
  previewApplied,
  previewLoading,
  previewReason,
  suggestionMenuOpen,
  templatePreviewLabel,
  templatePreviewText,
  canSend,
  resetStoryState,
  sendPrompt,
  stopGeneration,
  rollbackLast,
  regenerateLast,
  handleBranchSend,
  applySuggestedPrompt,
  previewTemplate,
  clearTemplatePreview,
  clearEnhancementPreview,
  requestEnhancedPrompt,
  applyEnhancedPrompt,
  applyTemplatePreview,
} = useStoryGeneration({
  currentStory,
  selectedWorldId,
  userInput: userInputDraft,
  selectedPersonaId,
  selectedContextEntryIds,
  selectedScriptDesignId,
  selectedScriptStageId,
  selectedScriptEventId,
  followScriptDesign,
  creationMode,
  progressIntent,
  runtimeStateId,
  selectedPrincipalCharacterId,
  dialogueMode,
  dialogueTarget,
  dialogueIntent,
  dialogueStyleHint,
  activeFocusTemplate,
  storyMode,
  authorsNote,
  instruction,
  configStore,
  storySessionStore,
  ensureV2Session,
  v2SessionId,
  clearPromptComposerSelection,
  onScrollToBottom: scrollToBottom,
  onFocusInput: () => {
    textareaRef.value?.focus()
  },
})

function openControlDrawer() {
  showControlDrawer.value = true
}

// ── Misc ───────────────────────────────────────────────────────────────────────
const controlBadgeText = computed(() => {
  const parts: string[] = []
  if (storyMode.value !== 'narrative') parts.push(modeLabels[storyMode.value])
  if (authorsNote.value) parts.push('旁白')
  if (storyMode.value === 'instruction' && instruction.value) parts.push('指令')
  return parts.join(' · ')
})

function handleKeydown(e: KeyboardEvent) {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault()
    if (canSend.value) sendPrompt()
  }
}

watch(() => currentStory.value?.id, async () => {
  const story = currentStory.value
  const metadata = story?.metadata ?? {}
  selectedScriptDesignId.value = typeof metadata.script_design_id === 'string' ? metadata.script_design_id : null
  selectedScriptStageId.value = typeof metadata.active_stage_id === 'string' ? metadata.active_stage_id : null
  selectedScriptEventId.value = typeof metadata.active_event_id === 'string' ? metadata.active_event_id : null
  followScriptDesign.value = metadata.follow_script_design === true
  creationMode.value = props.pageMode
  runtimeStateId.value = typeof metadata.runtime_state_id === 'string' ? metadata.runtime_state_id : null
  resetComposerState()
  resetStoryState(story)
  await hydrateRuntimeStateFromStory(story)
  await refreshEntityStateFromStory(story)
  if (props.pageMode === 'scripted') {
    creationMode.value = 'scripted'
    followScriptDesign.value = true
  }
  nextTick(() => scrollToBottom({ force: true }))
}, { immediate: true })

onActivated(async () => {
  const story = currentStory.value
  if (!story) return

  const metadata = story.metadata ?? {}
  selectedScriptDesignId.value = typeof metadata.script_design_id === 'string' ? metadata.script_design_id : selectedScriptDesignId.value
  selectedScriptStageId.value = typeof metadata.active_stage_id === 'string' ? metadata.active_stage_id : selectedScriptStageId.value
  selectedScriptEventId.value = typeof metadata.active_event_id === 'string' ? metadata.active_event_id : selectedScriptEventId.value
  runtimeStateId.value = typeof metadata.runtime_state_id === 'string' ? metadata.runtime_state_id : runtimeStateId.value
  if (props.pageMode === 'scripted') {
    creationMode.value = 'scripted'
    followScriptDesign.value = true
  }

  await hydrateRuntimeStateFromStory(story)
  await refreshEntityStateFromStory(story)
})

watch(selectedScriptDesign, (design) => {
  if (!design) {
    selectedScriptStageId.value = null
    selectedScriptEventId.value = null
    followScriptDesign.value = props.pageMode === 'scripted'
    return
  }

  const stageExists = design.stage_outlines.some((item) => item.id === selectedScriptStageId.value)
  if (!stageExists) {
    selectedScriptStageId.value = design.stage_outlines[0]?.id ?? null
  }

  const availableEvents = design.event_nodes.filter((item) => !selectedScriptStageId.value || item.stage_id === selectedScriptStageId.value)
  const eventExists = availableEvents.some((item) => item.id === selectedScriptEventId.value)
  if (!eventExists) {
    selectedScriptEventId.value = availableEvents[0]?.id ?? null
  }
})

watch(selectedScriptStageId, (stageId) => {
  if (!selectedScriptDesign.value) return
  const availableEvents = selectedScriptDesign.value.event_nodes.filter((item) => !stageId || item.stage_id === stageId)
  const eventExists = availableEvents.some((item) => item.id === selectedScriptEventId.value)
  if (!eventExists) {
    selectedScriptEventId.value = availableEvents[0]?.id ?? null
  }
})

watch(creationMode, (mode) => {
  if (mode === 'scripted') {
    followScriptDesign.value = true
  }
  if (props.pageMode === 'improv' && mode !== 'improv') {
    creationMode.value = 'improv'
  }
  if (props.pageMode === 'scripted' && mode !== 'scripted') {
    creationMode.value = 'scripted'
  }
})

function formatTime(ts: string) {
  try {
    return new Date(ts).toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
  } catch { return '' }
}

function syncStoryLocally(updatedStory: StoredStory) {
  const index = stories.value.findIndex((item) => item.id === updatedStory.id)
  if (index >= 0) {
    stories.value[index] = updatedStory
  }
  if (currentStory.value?.id === updatedStory.id) {
    Object.assign(currentStory.value, updatedStory)
  }
}

function syncRuntimeLocally(runtimeState: StoryRuntimeState) {
  runtimeStateId.value = runtimeState.id
  selectedScriptDesignId.value = runtimeState.script_design_id
  selectedScriptStageId.value = runtimeState.current_stage_id ?? null
  selectedScriptEventId.value = runtimeState.current_event_id ?? null
  creationMode.value = runtimeState.creation_mode
  followScriptDesign.value = runtimeState.creation_mode === 'scripted'

  if (!currentStory.value) return

  const metadata = {
    ...(currentStory.value.metadata ?? {}),
    runtime_state_id: runtimeState.id,
    script_design_id: runtimeState.script_design_id,
    creation_mode: runtimeState.creation_mode,
    follow_script_design: runtimeState.creation_mode === 'scripted',
    active_stage_id: runtimeState.current_stage_id,
    active_event_id: runtimeState.current_event_id,
  }

  currentStory.value.metadata = metadata

  const index = stories.value.findIndex((item) => item.id === currentStory.value?.id)
  if (index >= 0) {
    const existingStory = stories.value[index]
    if (!existingStory) return
    stories.value[index] = {
      ...existingStory,
      metadata: {
        ...(existingStory.metadata ?? {}),
        ...metadata,
      },
    }
  }
}

async function persistStoryProgress(progress: {
  script_design_id?: string | null
  active_stage_id?: string | null
  active_event_id?: string | null
  follow_script_design?: boolean
  creation_mode?: 'improv' | 'scripted' | null
  runtime_state_id?: string | null
}, successTitle: string) {
  if (!currentStory.value) return
  progressUpdating.value = true
  try {
    if (isScriptedPage.value) {
      const runtime = await storyLibraryApi.updateRuntime(currentStory.value.id, {
        script_design_id: progress.script_design_id ?? undefined,
        creation_mode: progress.creation_mode ?? undefined,
        current_stage_id: progress.active_stage_id ?? null,
        current_event_id: progress.active_event_id ?? null,
      })
      syncRuntimeLocally(runtime)
    } else {
      const updated = await storyLibraryApi.updateProgress(currentStory.value.id, progress)
      syncStoryLocally(updated)
    }
    toast({ title: successTitle })
  } catch {
    toast({ title: '推进保存失败', variant: 'destructive' })
  } finally {
    progressUpdating.value = false
  }
}

async function saveCurrentProgress() {
  await persistStoryProgress(
    {
      script_design_id: selectedScriptDesignId.value,
      active_stage_id: selectedScriptStageId.value,
      active_event_id: selectedScriptEventId.value,
      follow_script_design: followScriptDesign.value,
      creation_mode: creationMode.value,
      runtime_state_id: runtimeStateId.value,
    },
    '当前推进已保存',
  )
}

async function advanceToNextEvent() {
  const design = selectedScriptDesign.value
  if (!design || !selectedScriptEventId.value) return

  const stageScopedEvents = design.event_nodes.filter((item) => item.stage_id === selectedScriptStageId.value)
  const currentIndex = stageScopedEvents.findIndex((item) => item.id === selectedScriptEventId.value)
  const nextEvent = currentIndex >= 0 ? stageScopedEvents[currentIndex + 1] : null
  if (!nextEvent) return

  selectedScriptEventId.value = nextEvent.id
  await persistStoryProgress(
    {
      script_design_id: design.id,
      active_stage_id: selectedScriptStageId.value,
      active_event_id: nextEvent.id,
      follow_script_design: followScriptDesign.value,
      creation_mode: creationMode.value,
      runtime_state_id: runtimeStateId.value,
    },
    '已推进到下一事件',
  )
}

async function advanceToNextStage() {
  const design = selectedScriptDesign.value
  if (!design || !selectedScriptStageId.value) return

  const currentStageIndex = design.stage_outlines.findIndex((item) => item.id === selectedScriptStageId.value)
  const nextStage = currentStageIndex >= 0 ? design.stage_outlines[currentStageIndex + 1] : null
  if (!nextStage) return

  const nextStageFirstEvent = design.event_nodes.find((item) => item.stage_id === nextStage.id)
  selectedScriptStageId.value = nextStage.id
  selectedScriptEventId.value = nextStageFirstEvent?.id ?? null
  await persistStoryProgress(
    {
      script_design_id: design.id,
      active_stage_id: nextStage.id,
      active_event_id: nextStageFirstEvent?.id ?? null,
      follow_script_design: followScriptDesign.value,
      creation_mode: creationMode.value,
      runtime_state_id: runtimeStateId.value,
    },
    '已推进到下一阶段',
  )
}
</script>

<template>
  <div class="flex h-full bg-background">

    <StoryLibrarySidebar
      v-model:selected-world-id="selectedWorldId"
      :worlds="worlds ?? []"
      :worlds-loading="worldsLoading"
      :stories="stories"
      :stories-loading="storiesLoading"
      :current-story-id="currentStory?.id ?? null"
      @create-story="showNewStory = true"
      @select-story="selectStory"
      @delete-story="deleteStory"
    />

    <!-- ── Main Area ────────────────────────────────────────────────────── -->
    <div class="flex-1 flex flex-col min-w-0">
      <!-- Header -->
      <header class="h-12 flex items-center justify-between px-4 border-b border-border shrink-0">
        <div class="flex items-center gap-2 min-w-0">
          <Sparkles class="h-4 w-4 text-muted-foreground shrink-0" />
          <span v-if="currentStory" class="text-sm font-medium truncate">{{ currentStory.title }}</span>
          <span v-else class="text-sm text-muted-foreground">AI 故事创作</span>
          <Badge v-if="currentStory" variant="secondary" class="text-[11px] shrink-0">
            {{ currentStory.segments.length }} 段
          </Badge>
          <Badge
            variant="outline"
            :class="props.pageMode === 'scripted' ? 'border-orange-200 bg-orange-50 text-orange-900' : 'border-sky-200 bg-sky-50 text-sky-900'"
            class="text-[11px] shrink-0"
          >
            {{ pageModeLabel }}
          </Badge>
        </div>
        <div class="flex items-center gap-1">
          <RouterLink
            :to="alternateRoute"
            class="inline-flex h-7 items-center rounded-md border border-border px-2.5 text-xs text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
          >
            {{ alternateRouteLabel }}
          </RouterLink>
          <Button v-if="currentStory" size="sm" variant="ghost" class="h-7 gap-1.5 text-xs" @click="openControlDrawer">
            <PenLine class="h-3.5 w-3.5" />
            {{ controlDrawerTitle }}
            <Badge variant="secondary" class="ml-1 h-5 rounded-full px-2 text-[10px] font-normal">
              {{ controlDrawerBadgeText }}
            </Badge>
          </Button>
          <div v-if="currentStory" class="ml-1 inline-flex h-7 max-w-[11rem] items-center rounded-full border border-fuchsia-200 bg-fuchsia-50 px-2.5 text-[11px] text-fuchsia-900">
            <span class="truncate">主角：{{ selectedPersonaSummaryText }}</span>
          </div>
          <Button v-if="currentStory" size="sm" variant="ghost" class="h-7 gap-1.5 text-xs" @click="openPromptComposer">
            <Wand2 class="h-3.5 w-3.5" />
            {{ promptComposerButtonLabel }}
            <Badge variant="secondary" class="ml-1 h-5 rounded-full px-2 text-[10px] font-normal">
              {{ promptDrawerBadgeText }}
            </Badge>
          </Button>
          <Button v-if="currentStory" size="sm" variant="ghost" class="h-7 gap-1.5 text-xs" @click="showSidebar = !showSidebar">
            <ListOrdered class="h-3.5 w-3.5" />
            设定 / 记忆
            <ChevronRight :class="cn('h-3 w-3 transition-transform', showSidebar && 'rotate-90')" />
          </Button>
        </div>
      </header>

      <div class="flex-1 flex min-h-0">
        <!-- Story + Controls + Input -->
        <div class="flex-1 flex flex-col min-w-0">
          <!-- Story scroll -->
          <div ref="scrollRef" class="flex-1 overflow-y-auto px-6 py-4 space-y-6" @scroll="handleStoryScroll">
            <StoryConversationList
              :current-story="currentStory"
              :generating="generating"
              :format-time="formatTime"
              @branch-send="handleBranchSend"
              @rollback-last="rollbackLast"
              @regenerate-last="regenerateLast"
            />
          </div>

          <!-- Input Bar -->
          <div class="px-4 py-3 border-t border-border shrink-0">
            <div class="max-w-3xl mx-auto space-y-2.5">
              <div
                v-if="isScriptedPage"
                class="grid gap-2 rounded-md border border-border/70 bg-muted/20 px-3 py-2 md:grid-cols-[minmax(0,1fr)_minmax(0,1fr)]"
              >
                <div class="flex items-center justify-between gap-3 rounded-md border border-orange-200/70 bg-orange-50/70 px-3 py-2">
                  <div class="min-w-0 text-xs text-foreground">
                    <p class="font-medium text-orange-950">剧本推进</p>
                    <p class="mt-0.5 text-[11px] text-orange-800/80">打开侧边推进面板，统一调整剧本、阶段、事件和推进意图。</p>
                  </div>
                  <Button
                    v-if="currentStory"
                    size="sm"
                    variant="outline"
                    class="h-8 shrink-0 gap-1.5 border-orange-200 bg-white text-xs text-orange-900 hover:bg-orange-100"
                    @click="showScriptSidebar = !showScriptSidebar"
                  >
                    <Route class="h-3.5 w-3.5" />
                    剧本推进
                    <ChevronRight :class="cn('h-3 w-3 transition-transform', showScriptSidebar && 'rotate-90')" />
                  </Button>
                </div>

                <div class="flex items-center justify-between gap-3 rounded-md border border-sky-200/70 bg-sky-50/60 px-3 py-2">
                  <div class="min-w-0 text-xs text-foreground">
                    <p class="font-medium text-sky-950">{{ inputAssistTitle }}</p>
                    <p class="mt-0.5 text-[11px] text-sky-800/80">{{ inputAssistDescription }}</p>
                  </div>
                  <Button
                    size="sm"
                    variant="secondary"
                    class="h-8 shrink-0 gap-1.5 text-xs"
                    :disabled="!currentStory || generating || !userInput.trim() || previewLoading"
                    @click="requestEnhancedPrompt"
                  >
                    <LoaderCircle v-if="previewLoading" class="h-3.5 w-3.5 animate-spin" />
                    <Wand2 v-else class="h-3.5 w-3.5" />
                    {{ inputAssistButtonLabel }}
                  </Button>
                </div>
              </div>

              <div
                v-else
                class="flex items-center justify-between rounded-md border border-border/70 bg-muted/20 px-3 py-2"
              >
                <div class="text-xs text-foreground">
                  <p class="font-medium">{{ inputAssistTitle }}</p>
                  <p class="text-[11px] text-muted-foreground mt-0.5">{{ inputAssistDescription }}</p>
                </div>
                <div class="flex items-center gap-2">
                  <Button
                    size="sm"
                    variant="secondary"
                    class="h-8 gap-1.5 text-xs"
                    :disabled="!currentStory || generating || !userInput.trim() || previewLoading"
                    @click="requestEnhancedPrompt"
                  >
                    <LoaderCircle v-if="previewLoading" class="h-3.5 w-3.5 animate-spin" />
                    <Wand2 v-else class="h-3.5 w-3.5" />
                    {{ inputAssistButtonLabel }}
                  </Button>
                </div>
              </div>
              <div
                v-if="previewSourceText && !previewLoading"
                class="rounded-md border border-cyan-200/70 bg-cyan-50/60 px-3 py-2 text-xs text-foreground"
              >
                <div class="flex items-center justify-between gap-3">
                  <p class="flex items-center gap-1.5 font-medium text-cyan-800">
                    <Sparkles class="h-3.5 w-3.5" />
                    增强 Prompt 结果
                  </p>
                </div>
                <div class="mt-2 space-y-2">
                  <div class="rounded-md border border-cyan-200/80 bg-white/80 px-3 py-2">
                    <p class="font-medium text-cyan-900">{{ inputPreviewOriginalLabel }}</p>
                    <p class="mt-1.5 whitespace-pre-wrap leading-5 text-cyan-950">{{ previewSourceText }}</p>
                  </div>
                  <div class="rounded-md border border-cyan-300 bg-white px-3 py-2">
                    <p class="font-medium text-cyan-900">{{ inputPreviewEnhancedLabel }}</p>
                    <p class="mt-1.5 whitespace-pre-wrap leading-5 text-cyan-950">{{ enhancedInputPreview || previewSourceText }}</p>
                  </div>
                </div>
                <p class="mt-1 text-[11px] text-cyan-800/80">
                  <template v-if="previewApplied">
                    {{ isScriptedPage ? '如果认可这段微调说明，可以填入输入框辅助本轮表现，但不会改写主线推进。' : '如果你认可这段增强结果，可以手动填入输入框后再发送。' }}
                  </template>
                  <template v-else-if="previewReason === 'input_too_long'">当前输入较长，增强结果与原始 Prompt 保持一致。</template>
                  <template v-else-if="previewReason === 'preview_failed'">增强失败，请保留原始 Prompt 或稍后重试。</template>
                  <template v-else>当前增强结果与原始 Prompt 一致。</template>
                </p>
                <div class="mt-2 flex items-center justify-end gap-2">
                  <Button size="sm" variant="ghost" class="h-8 px-3 text-xs" @click="clearEnhancementPreview">
                    关闭
                  </Button>
                  <Button
                    size="sm"
                    class="h-8 px-3 text-xs"
                    :disabled="!previewApplied || !enhancedInputPreview.trim()"
                    @click="applyEnhancedPrompt"
                  >
                    填入输入框
                  </Button>
                </div>
              </div>
              <div
                v-if="templatePreviewText"
                class="rounded-md border border-amber-200/80 bg-amber-50/70 px-3 py-2 text-xs text-foreground"
              >
                <div class="flex items-center justify-between gap-3">
                  <p class="flex items-center gap-1.5 font-medium text-amber-900">
                    <Wand2 class="h-3.5 w-3.5" />
                    {{ templatePreviewTitle }}
                  </p>
                  <Badge variant="secondary" class="text-[10px]">
                    {{ templatePreviewLabel || '模板' }}
                  </Badge>
                </div>
                <div class="mt-2 rounded-md border border-amber-200 bg-white/90 px-3 py-2">
                  <p class="font-medium text-amber-950">模板内容</p>
                  <p class="mt-1.5 whitespace-pre-wrap leading-5 text-amber-950">{{ templatePreviewText }}</p>
                </div>
                <p class="mt-2 text-[11px] text-amber-900/80">模板不会直接写入输入框，确认后再手动填入。</p>
                <div class="mt-2 flex items-center justify-end gap-2">
                  <Button size="sm" variant="ghost" class="h-8 px-3 text-xs" @click="clearTemplatePreview">
                    关闭
                  </Button>
                  <Button size="sm" class="h-8 px-3 text-xs" @click="applyTemplatePreview">
                    填入输入框
                  </Button>
                </div>
              </div>
              <div class="relative">
                <Textarea
                  ref="textareaRef"
                  :id="promptInputDomId"
                  :name="promptInputName"
                  :data-mode="props.pageMode"
                  v-model="userInput"
                  :disabled="!currentStory || generating"
                  :placeholder="inputPlaceholder"
                  class="min-h-[72px] max-h-[140px] resize-none pr-24 text-sm"
                  @input="clearEnhancementPreview"
                  @keydown="handleKeydown"
                />
                <DropdownMenu v-model:open="suggestionMenuOpen">
                  <DropdownMenuTrigger as-child>
                    <Button
                      size="icon"
                      variant="ghost"
                      class="absolute bottom-2 right-12 h-8 w-8"
                      :disabled="!currentStory || generating"
                    >
                      <CircleHelp class="h-4 w-4" />
                    </Button>
                  </DropdownMenuTrigger>
                  <DropdownMenuContent align="end" class="w-[24rem] p-0">
                    <div v-if="isScriptedPage" class="space-y-2 p-3 text-xs">
                      <div class="rounded-lg border border-sky-200/70 bg-sky-50/70 px-3 py-2.5">
                        <p class="font-medium text-sky-900">微调说明</p>
                        <p class="mt-1 text-[11px] leading-5 text-sky-800/80">
                          严格剧本模式中，这里的输入只调整本轮表现，不决定主线推进。
                        </p>
                      </div>
                      <div class="space-y-2 rounded-lg border border-border bg-background px-3 py-3">
                        <p
                          v-for="item in scriptedMicroAdjustHelp"
                          :key="item"
                          class="leading-5 text-foreground"
                        >
                          {{ item }}
                        </p>
                      </div>
                    </div>
                    <div v-else class="max-h-[26rem] overflow-y-auto p-2">
                      <StoryInputSuggestions
                        :choices="lastChoices"
                        :disabled="!currentStory || generating"
                        @pick="applySuggestedPrompt"
                        @preview-template="previewTemplate"
                      />
                    </div>
                  </DropdownMenuContent>
                </DropdownMenu>
                <div class="absolute bottom-2 right-2">
                  <Button v-if="generating" size="icon" variant="destructive" class="h-8 w-8" @click="stopGeneration">
                    <Square class="h-3.5 w-3.5" />
                  </Button>
                  <Button v-else size="icon" class="h-8 w-8" :disabled="!canSend" @click="sendPrompt()">
                    <Send class="h-3.5 w-3.5" />
                  </Button>
                </div>
              </div>
              <p class="text-[11px] text-muted-foreground mt-1.5 flex items-center gap-2 flex-wrap">
                <span>SSE 流式 · RAG 已启用</span>
                <span class="text-primary font-medium">· 创作模式：{{ creationMode === 'scripted' ? '严格剧本' : '渐进式' }}</span>
                <span v-if="creationMode === 'scripted'" class="text-orange-600">· 推进意图：{{ progressIntent === 'complete' ? '完成事件' : progressIntent === 'advance' ? '推进事件' : '仅描写' }}</span>
                <span v-if="isScriptedPage" class="text-orange-700">· 主线推进由剧本运行态决定</span>
                <span v-if="!isScriptedPage && storyMode !== 'narrative'" class="text-primary font-medium">· 模式：{{ modeLabels[storyMode] }}</span>
                <span v-if="!isScriptedPage && authorsNote" class="text-amber-500">· 旁白已设置</span>
                <span v-if="!isScriptedPage && storyMode === 'instruction' && instruction" class="text-violet-500">· 指令已设置</span>
                <span v-if="selectedPersona" class="text-fuchsia-600">· 主角人设：{{ selectedPersona.name }}</span>
                <span v-if="selectedPrincipalCharacter" class="text-amber-600">· 关键角色：{{ selectedPrincipalCharacter.name }}</span>
                <span v-if="selectedPrincipalCharacter && dialogueMode !== 'auto'" class="text-orange-500">· 对白模式：{{ dialogueMode === 'required' ? '本轮必须对白' : '优先发言' }}</span>
                <span v-if="selectedContextEntries.length" class="text-emerald-600">· 显式设定优先于 RAG</span>
                <span v-if="activeFocusTemplate" class="text-sky-600">· 本轮重点：{{ activeFocusTemplate.label }}</span>
                <span v-if="previewSourceText" class="text-cyan-600">· 已生成增强 Prompt 结果</span>
                <span v-if="templatePreviewText" class="text-amber-600">· 已预览指令模板</span>
              </p>
            </div>
          </div>
        </div>

        <!-- Context / Memory Sidebar -->
        <transition
          enter-active-class="transition-all duration-200"
          enter-from-class="opacity-0 translate-x-4"
          enter-to-class="opacity-100 translate-x-0"
          leave-active-class="transition-all duration-150"
          leave-from-class="opacity-100 translate-x-0"
          leave-to-class="opacity-0 translate-x-4"
        >
          <StoryScriptSidebar
            v-if="showScriptSidebar && isScriptedPage"
            :selected-script-design-id="selectedScriptDesignId ?? NONE_OPTION_VALUE"
            :selected-script-stage-id="selectedScriptStageId ?? NONE_OPTION_VALUE"
            :selected-script-event-id="selectedScriptEventId ?? NONE_OPTION_VALUE"
            :progress-intent="progressIntent"
            :script-designs="scriptDesigns"
            :script-stages="scriptStages"
            :script-events="scriptEvents"
            :none-option-value="NONE_OPTION_VALUE"
            :progress-updating="progressUpdating"
            :can-advance-event="scriptEvents.length > 0 && !!selectedScriptEventId && scriptEvents[scriptEvents.length - 1]?.id !== selectedScriptEventId"
            :can-advance-stage="scriptStages.length > 0 && !!selectedScriptStageId && scriptStages[scriptStages.length - 1]?.id !== selectedScriptStageId"
            @close="showScriptSidebar = false"
            @update:progress-intent="progressIntent = $event"
            @update:selected-script-design-id="selectedScriptDesignId = $event === NONE_OPTION_VALUE ? null : $event"
            @update:selected-script-stage-id="selectedScriptStageId = $event === NONE_OPTION_VALUE ? null : $event"
            @update:selected-script-event-id="selectedScriptEventId = $event === NONE_OPTION_VALUE ? null : $event"
            @save-progress="saveCurrentProgress"
            @advance-event="advanceToNextEvent"
            @advance-stage="advanceToNextStage"
          />
        </transition>

        <transition
          enter-active-class="transition-all duration-200"
          enter-from-class="opacity-0 translate-x-4"
          enter-to-class="opacity-100 translate-x-0"
          leave-active-class="transition-all duration-150"
          leave-from-class="opacity-100 translate-x-0"
          leave-to-class="opacity-0 translate-x-4"
        >
          <StoryMemorySidebar
            v-if="showSidebar"
            :show-script-progress="!isScriptedPage"
            :script-design-title="selectedScriptDesign?.title ?? null"
            :active-stage-title="activeScriptStage?.title ?? null"
            :active-event-title="activeScriptEvent?.title ?? null"
            :follow-script-design="followScriptDesign"
            :can-advance-event="scriptEvents.length > 0 && !!selectedScriptEventId && scriptEvents[scriptEvents.length - 1]?.id !== selectedScriptEventId"
            :can-advance-stage="scriptStages.length > 0 && !!selectedScriptStageId && scriptStages[scriptStages.length - 1]?.id !== selectedScriptStageId"
            :progress-updating="progressUpdating"
            :last-summary="currentSummarySnapshot"
            :last-summary-diff="lastSummaryDiff"
            :last-contexts="lastContexts"
            :last-memory-updates="currentMemoryUpdates"
            :last-entity-state="currentEntityStateSnapshot"
            :last-entity-state-updates="currentEntityStateUpdates"
            :last-world-update="currentWorldUpdate"
            @save-progress="saveCurrentProgress"
            @advance-event="advanceToNextEvent"
            @advance-stage="advanceToNextStage"
          />
        </transition>
      </div>
    </div>
  </div>

  <!-- New Story Dialog -->
  <Dialog v-model:open="showNewStory">
    <DialogContent class="sm:max-w-md">
      <DialogHeader><DialogTitle>新建故事</DialogTitle></DialogHeader>
      <div class="space-y-4 py-2">
        <div class="space-y-2">
          <Label for="story-title">故事标题</Label>
          <Input id="story-title" v-model="newStoryTitle" placeholder="未命名故事" @keydown.enter="createStory" />
        </div>
        <div v-if="selectedWorldId && worlds" class="text-sm text-muted-foreground">
          世界：{{ worlds.find(w => w.id === selectedWorldId)?.name }}
        </div>
      </div>
      <DialogFooter>
        <Button variant="outline" @click="showNewStory = false">取消</Button>
        <Button :disabled="!newStoryTitle.trim() || creatingStory" @click="createStory">
          {{ creatingStory ? '创建中…' : '创建' }}
        </Button>
      </DialogFooter>
    </DialogContent>
  </Dialog>

  <StoryControlDrawer
    :open="showControlDrawer"
    :page-mode="props.pageMode"
    :panel-title="controlDrawerTitle"
    :show-control-panel="showControlPanel"
    :story-mode="storyMode"
    :authors-note="authorsNote"
    :instruction="instruction"
    :control-badge-text="controlBadgeText"
    :mode-labels="modeLabels"
    :selected-persona-name="selectedPersona?.name ?? null"
    :selected-persona-select-value="selectedPersonaSelectValue"
    :selected-script-design-id="selectedScriptDesignId ?? NONE_OPTION_VALUE"
    :selected-script-stage-id="selectedScriptStageId ?? NONE_OPTION_VALUE"
    :selected-script-event-id="selectedScriptEventId ?? NONE_OPTION_VALUE"
    :follow-script-design="followScriptDesign"
    :selected-principal-character-id="selectedPrincipalCharacterId ?? NONE_OPTION_VALUE"
    :dialogue-mode="dialogueMode"
    :dialogue-target="dialogueTarget"
    :dialogue-intent="dialogueIntent"
    :dialogue-style-hint="dialogueStyleHint"
    :none-option-value="NONE_OPTION_VALUE"
    :personas="personas"
    :script-designs="scriptDesigns"
    :script-stages="scriptStages"
    :script-events="scriptEvents"
    :principal-characters="lorebookCharacterEntries"
    :personas-loading="personasLoading"
    :generating="generating"
    @update:open="showControlDrawer = $event"
    @update:show-control-panel="showControlPanel = $event"
    @update:story-mode="storyMode = $event"
    @update:authors-note="authorsNote = $event"
    @update:instruction="instruction = $event"
    @update:selected-persona-select-value="selectedPersonaSelectValue = $event"
    @update:selected-script-design-id="selectedScriptDesignId = $event === NONE_OPTION_VALUE ? null : $event"
    @update:selected-script-stage-id="selectedScriptStageId = $event === NONE_OPTION_VALUE ? null : $event"
    @update:selected-script-event-id="selectedScriptEventId = $event === NONE_OPTION_VALUE ? null : $event"
    @update:follow-script-design="followScriptDesign = $event"
    @update:selected-principal-character-id="selectedPrincipalCharacterId = $event === NONE_OPTION_VALUE ? null : $event"
    @update:dialogue-mode="dialogueMode = $event"
    @update:dialogue-target="dialogueTarget = $event"
    @update:dialogue-intent="dialogueIntent = $event"
    @update:dialogue-style-hint="dialogueStyleHint = $event"
  />

  <StoryPromptComposerSheet
    :open="showPromptComposer"
    :generating="generating"
    :selected-context-entries="selectedContextEntries"
    :active-focus-template="activeFocusTemplate"
    :composer-search-query="composerSearchQuery"
    :current-composer-tab="currentComposerTab"
    :filtered-character-entries="filteredCharacterEntries"
    :filtered-location-entries="filteredLocationEntries"
    :filtered-event-entries="filteredEventEntries"
    :composer-preview-entry="composerPreviewEntry"
    :lorebook-entries-loading="lorebookEntriesLoading"
    :prompt-focus-templates="promptFocusTemplates"
    :draft-focus-template-id="draftFocusTemplateId"
    :is-draft-entry-selected="isDraftEntrySelected"
    @update:open="showPromptComposer = $event"
    @update:composer-search-query="composerSearchQuery = $event"
    @update:current-composer-tab="currentComposerTab = $event"
    @update:draft-focus-template-id="draftFocusTemplateId = $event"
    @clear="clearPromptComposerSelection"
    @remove-entry="removeSelectedContextEntry"
    @clear-focus-template="clearSelectedFocusTemplate"
    @open-entry="openComposerEntry"
    @toggle-entry="toggleDraftContextEntry"
    @apply="applyPromptComposerSelection"
  />
</template>
