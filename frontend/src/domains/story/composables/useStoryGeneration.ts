/**
 * 文件说明：前端业务域逻辑与接口封装。
 */

import { computed, nextTick, onUnmounted, ref, type ComputedRef, type Ref } from 'vue'
import { useToast } from '@/components/ui/toast'
import {
  type EntityStateUpdate,
  type MemoryUpdateEvent,
  previewEnhancedStoryInput,
  regenerateStoryApi,
  rollbackLastMessageApi,
  streamStoryV2,
  type StoryActivationLog,
} from '@/domains/story/api/storyGenerationApi'
import type { SummaryMemorySnapshot } from '@/domains/story/api/storyGenerationApi'
import type { PromptFocusTemplate } from '@/config/prompts'
import type { StoryMode, StorySegment, StoredStory } from '@/components/story/types'
import type { useConfigStore } from '@/stores/config'
import type { useStorySessionStore } from '@/stores/storySession'
import { storyLibraryApi, type StoryRuntimeState } from '@/domains/story/api/storyLibraryApi'

interface StoryContextHit {
  label: string
  detail: string
  source: 'explicit' | 'rag' | 'rule'
}

interface StorySummaryDiff {
  summaryChanged: boolean
  newFacts: string[]
  removedFacts: string[]
  previousLastTurn: number | null
  currentLastTurn: number | null
}

interface UseStoryGenerationArgs {
  currentStory: Ref<StoredStory | null>
  selectedWorldId: Ref<string>
  userInput?: Ref<string>
  selectedPersonaId: Ref<string | null>
  selectedContextEntryIds: Ref<string[]>
  selectedScriptDesignId: Ref<string | null>
  selectedScriptStageId: Ref<string | null>
  selectedScriptEventId: Ref<string | null>
  followScriptDesign: Ref<boolean>
  creationMode: Ref<'improv' | 'scripted'>
  progressIntent: Ref<'hold' | 'advance' | 'complete'>
  runtimeStateId: Ref<string | null>
  selectedPrincipalCharacterId: Ref<string | null>
  dialogueMode: Ref<'auto' | 'focused' | 'required'>
  dialogueTarget: Ref<string>
  dialogueIntent: Ref<string>
  dialogueStyleHint: Ref<string>
  activeFocusTemplate: ComputedRef<PromptFocusTemplate | null>
  storyMode: Ref<StoryMode>
  authorsNote: Ref<string>
  instruction: Ref<string>
  configStore: ReturnType<typeof useConfigStore>
  storySessionStore: ReturnType<typeof useStorySessionStore>
  ensureV2Session: (storyId: string) => Promise<string>
  v2SessionId: Ref<string>
  clearPromptComposerSelection: () => void
  onScrollToBottom?: (options?: { force?: boolean }) => void
  onFocusInput?: () => void
}

/** 功能：函数 parseChoices，负责 parseChoices 相关处理。 */
function parseChoices(text: string): string[] {
  const re = /\[(?:选项\s*\d+|[A-Z])\]\s*([^\[\n]+)/g
  const results: string[] = []
  let match: RegExpExecArray | null
  while ((match = re.exec(text)) !== null) {
    const choiceText = match[1]?.trim()
    if (choiceText) results.push(choiceText)
  }
  return results
}

/** 功能：函数 formatActivationHits，负责 formatActivationHits 相关处理。 */
function formatActivationHits(logs: StoryActivationLog[]): StoryContextHit[] {
  return logs
    .filter((log) => {
      if (!log.entry_name) return false
      if (log.selection_mode === 'explicit' || log.selection_mode === 'rag') return true
      return ['rule', 'vector', 'hybrid', 'bm25'].includes(String(log.source ?? ''))
    })
    .map((log) => {
      let source: StoryContextHit['source'] = 'rag'
      let label = 'RAG 补充命中'
      if (log.selection_mode === 'explicit') {
        source = 'explicit'
        label = '用户显式选择'
      } else if (String(log.source ?? '') === 'rule') {
        source = 'rule'
        label = '规则命中'
      }
      const typeLabel = log.entry_type ? `[${log.entry_type}] ` : ''
      return {
        label,
        detail: `${typeLabel}${log.entry_name}`,
        source,
      }
    })
}

/** 功能：函数 buildSummaryDiff，负责 buildSummaryDiff 相关处理。 */
function buildSummaryDiff(
  previous: SummaryMemorySnapshot | null | undefined,
  next: SummaryMemorySnapshot | null | undefined,
): StorySummaryDiff | null {
  if (!previous && !next) return null
  const previousFacts = new Set(previous?.key_facts ?? [])
  const nextFacts = new Set(next?.key_facts ?? [])
  const newFacts = Array.from(nextFacts).filter((fact) => !previousFacts.has(fact))
  const removedFacts = Array.from(previousFacts).filter((fact) => !nextFacts.has(fact))
  const summaryChanged = (previous?.summary_text ?? '') !== (next?.summary_text ?? '')

  return {
    summaryChanged,
    newFacts,
    removedFacts,
    previousLastTurn: previous?.last_turn ?? null,
    currentLastTurn: next?.last_turn ?? null,
  }
}

/** 功能：函数 hydrateSummarySnapshotFromStore，负责 hydrateSummarySnapshotFromStore 相关处理。 */
function hydrateSummarySnapshotFromStore(
  summaryRecord:
    | {
        summary_text: string
        key_facts: string[]
        last_turn: number
      }
    | null
    | undefined,
  sessionId: string,
): SummaryMemorySnapshot | null {
  if (!summaryRecord) return null
  return {
    summary_text: summaryRecord.summary_text,
    key_facts: summaryRecord.key_facts,
    last_turn: summaryRecord.last_turn,
    session_id: sessionId,
  }
}

/** 功能：函数 extractContextHitsFromUpdates，负责 extractContextHitsFromUpdates 相关处理。 */
function extractContextHitsFromUpdates(events: MemoryUpdateEvent[]): StoryContextHit[] {
  return events
    .filter((event) => event.memory_layer === 'episodic' && event.memory_key === 'conversation_history_index')
    .map((event) => ({
      label: event.title,
      detail: event.reason ?? '历史上下文已参与本轮修复或更新',
      source: 'rag' as const,
    }))
}

/** 功能：函数 useStoryGeneration，负责 useStoryGeneration 相关处理。 */
export function useStoryGeneration(args: UseStoryGenerationArgs) {
  const { toast } = useToast()

  const userInput = args.userInput ?? ref('')
  const generating = ref(false)
  const abortController = ref<AbortController | null>(null)
  const previewAbortController = ref<AbortController | null>(null)

  const lastCommittedNodeId = ref<string | null>(null)
  const lastChoices = ref<string[]>([])
  const lastContexts = ref<StoryContextHit[]>([])
  const lastSummary = ref<SummaryMemorySnapshot | null>(null)
  const lastMemoryUpdates = ref<MemoryUpdateEvent[]>([])
  const lastEntityStateUpdates = ref<EntityStateUpdate[]>([])
  const lastWorldUpdate = ref<Record<string, unknown> | null>(null)
  const lastSummaryDiff = ref<StorySummaryDiff | null>(null)

  function applyRuntimeSnapshot(runtimeState: Record<string, unknown> | StoryRuntimeState | null | undefined) {
    if (!runtimeState) return
    if (typeof runtimeState.id === 'string') {
      args.runtimeStateId.value = runtimeState.id
      if (args.currentStory.value) args.currentStory.value.metadata.runtime_state_id = runtimeState.id
    }
    if (typeof runtimeState.current_stage_id === 'string') {
      args.selectedScriptStageId.value = runtimeState.current_stage_id
      if (args.currentStory.value) args.currentStory.value.metadata.active_stage_id = runtimeState.current_stage_id
    }
    if (typeof runtimeState.current_event_id === 'string') {
      args.selectedScriptEventId.value = runtimeState.current_event_id
      if (args.currentStory.value) args.currentStory.value.metadata.active_event_id = runtimeState.current_event_id
    }
  }

  const previewSourceText = ref('')
  const enhancedInputPreview = ref('')
  const previewApplied = ref(false)
  const previewLoading = ref(false)
  const previewReason = ref<string | null>(null)

  const suggestionMenuOpen = ref(false)
  const templatePreviewLabel = ref('')
  const templatePreviewText = ref('')

  const canSend = computed(() => {
    return !!userInput.value.trim() && !!args.currentStory.value && !generating.value
  })

  function scrollToBottom(options?: { force?: boolean }) {
    args.onScrollToBottom?.(options)
  }

  function focusInput() {
    args.onFocusInput?.()
  }

  function clearTemplatePreview() {
    templatePreviewLabel.value = ''
    templatePreviewText.value = ''
  }

  function clearEnhancementPreview() {
    previewAbortController.value?.abort()
    previewAbortController.value = null
    previewLoading.value = false
    previewSourceText.value = ''
    enhancedInputPreview.value = ''
    previewApplied.value = false
    previewReason.value = null
  }

  function resetStoryState(story: StoredStory | null) {
    abortController.value?.abort()
    clearEnhancementPreview()
    clearTemplatePreview()
    generating.value = false
    abortController.value = null
    lastContexts.value = []
    lastSummary.value = null
    lastMemoryUpdates.value = []
    lastEntityStateUpdates.value = []
    lastWorldUpdate.value = null
    lastSummaryDiff.value = null
    lastCommittedNodeId.value = null
    lastChoices.value = story?.segments[story.segments.length - 1]?.choices ?? []
  }

  async function sendPrompt(overridePrompt?: string, chosenIdx?: number) {
    const rawPrompt = (overridePrompt ?? userInput.value).trim()
    if (!rawPrompt || !args.currentStory.value || generating.value) return

    const prompt = rawPrompt
    let generationCompleted = false
    const parentNodeId = lastCommittedNodeId.value
    const existingSegmentCount = args.currentStory.value.segments.length
    const pendingSegmentId = `tmp-${Date.now()}`
    const pendingSegment: StorySegment = {
      id: pendingSegmentId,
      prompt,
      creation_mode: args.creationMode.value,
      content: '',
      choices: [],
      retrieved_context: [],
      runtime_state_snapshot: null,
      timestamp: new Date().toISOString(),
    }

    args.currentStory.value.segments.push(pendingSegment)
    const segment = args.currentStory.value.segments[existingSegmentCount]
    if (!segment) return
    if (!overridePrompt) userInput.value = ''
    clearEnhancementPreview()
    generating.value = true
    abortController.value = new AbortController()
    await nextTick()
    scrollToBottom({ force: true })

    const storyId = args.currentStory.value.id
    const sessionId = await args.ensureV2Session(storyId)
    let runtimeInitialSnapshot: Record<string, unknown> | StoryRuntimeState | null = null
    if (
      args.creationMode.value === 'scripted'
      && existingSegmentCount === 0
      && !args.currentStory.value.metadata?.runtime_initial_snapshot
      && args.selectedScriptDesignId.value
    ) {
      try {
        runtimeInitialSnapshot = await storyLibraryApi.getRuntime(storyId)
      } catch {
        runtimeInitialSnapshot = null
      }
    }
    const storyScriptMetadata = {
      script_design_id: args.selectedScriptDesignId.value,
      active_stage_id: args.selectedScriptStageId.value,
      active_event_id: args.selectedScriptEventId.value,
      follow_script_design: args.followScriptDesign.value,
      creation_mode: args.creationMode.value,
      runtime_state_id: args.runtimeStateId.value,
      ...(runtimeInitialSnapshot ? { runtime_initial_snapshot: runtimeInitialSnapshot } : {}),
    }

    try {
      const updatedStory = await storyLibraryApi.update(storyId, {
        metadata: storyScriptMetadata,
      })
      if (args.currentStory.value?.id === storyId) {
        const localSegments = args.currentStory.value.segments
        Object.assign(args.currentStory.value, updatedStory, { segments: localSegments })
      }
    } catch {
      // Binding persistence failure should not block generation.
    }

    const mergedContextEntryIds = Array.from(
      new Set(
        [
          ...args.selectedContextEntryIds.value,
          ...(args.selectedPrincipalCharacterId.value ? [args.selectedPrincipalCharacterId.value] : []),
        ].filter(Boolean),
      ),
    )
    const storyGenerationModel = args.configStore.getResolvedSceneModel('story_generation')

    const payload = {
      ...(storyGenerationModel.provider
        ? {
            provider: storyGenerationModel.provider,
            base_url: storyGenerationModel.base_url,
          }
        : {}),
      session_id: sessionId,
      story_id: storyId,
      user_input: prompt,
      world_id: args.selectedWorldId.value || undefined,
      creation_mode: args.creationMode.value,
      progress_intent: args.progressIntent.value,
      runtime_state_id: args.runtimeStateId.value || undefined,
      allow_state_transition: args.creationMode.value === 'scripted',
      persona_id: args.selectedPersonaId.value || undefined,
      script_design_id: args.selectedScriptDesignId.value || undefined,
      active_stage_id: args.selectedScriptStageId.value || undefined,
      active_event_id: args.selectedScriptEventId.value || undefined,
      follow_script_design: args.followScriptDesign.value,
      principal_character_id: args.selectedPrincipalCharacterId.value || undefined,
      dialogue_mode: args.dialogueMode.value,
      dialogue_target: args.dialogueTarget.value.trim() || undefined,
      dialogue_intent: args.dialogueIntent.value.trim() || undefined,
      dialogue_style_hint: args.dialogueStyleHint.value.trim() || undefined,
      force_dialogue_round: args.dialogueMode.value === 'required',
      use_rag: true,
      model: storyGenerationModel.model,
      temperature: args.configStore.config.temperature,
      max_tokens: args.configStore.config.maxTokens,
      authors_note: args.authorsNote.value || undefined,
      mode: args.storyMode.value,
      instruction: args.storyMode.value === 'instruction' ? (args.instruction.value || undefined) : undefined,
      selected_context_entry_ids: mergedContextEntryIds,
      focus_instruction: args.activeFocusTemplate.value?.instruction,
      focus_label: args.activeFocusTemplate.value?.label,
      enhance_input: false,
    }

    try {
      for await (const event of streamStoryV2(payload, abortController.value.signal)) {
        if (event.type === 'chunk' && event.content) {
          segment.content += event.content
          nextTick(() => scrollToBottom())
        } else if (event.type === 'done') {
          if (event.generated_text) segment.content = event.generated_text
          segment.id = `seg-${Date.now()}`
          const streamChoices = Array.isArray(event.choices) ? event.choices.filter(Boolean) : []
          segment.choices = streamChoices.length ? streamChoices : parseChoices(segment.content)
          if (!event.generated_text && segment.choices.length) {
            segment.content = segment.content.replace(/\n?\[[A-Z]\]\s*[^\n]*/g, '').trimEnd()
          }
          lastChoices.value = segment.choices
          if (event.activation_logs?.length) {
            const contextHits = formatActivationHits(event.activation_logs)
            segment.retrieved_context = contextHits.map((item) => `${item.label} · ${item.detail}`)
            lastContexts.value = contextHits
          }
          if (event.memory_updates?.length) {
            lastMemoryUpdates.value = event.memory_updates
            args.storySessionStore.appendMemoryEvents(
              sessionId,
              args.currentStory.value?.title ?? '',
              args.selectedWorldId.value,
              event.memory_updates,
            )
          } else {
            lastMemoryUpdates.value = []
          }
          const previousSummary = args.storySessionStore.getSummarySnapshot(sessionId) ?? lastSummary.value
          if (event.summary_memory_snapshot) {
            lastSummaryDiff.value = buildSummaryDiff(previousSummary, event.summary_memory_snapshot)
            lastSummary.value = event.summary_memory_snapshot
            args.storySessionStore.updateSummary({
              sessionId,
              storyTitle: args.currentStory.value?.title ?? '',
              worldId: args.selectedWorldId.value,
              summary_text: event.summary_memory_snapshot.summary_text,
              key_facts: event.summary_memory_snapshot.key_facts ?? [],
              last_turn: event.summary_memory_snapshot.last_turn ?? 0,
              updatedAt: new Date().toISOString(),
            })
          } else if (event.memory_updates?.some((item) => item.memory_layer === 'semantic' && item.action === 'reset')) {
            lastSummaryDiff.value = buildSummaryDiff(previousSummary, null)
            lastSummary.value = null
          }
          if (event.runtime_state_snapshot) {
            segment.runtime_state_snapshot = event.runtime_state_snapshot
            applyRuntimeSnapshot(event.runtime_state_snapshot)
          }
          if (event.entity_state_snapshot) {
            args.storySessionStore.updateEntityStateSnapshot(event.entity_state_snapshot)
          }
          if (event.entity_state_updates?.length) {
            lastEntityStateUpdates.value = event.entity_state_updates
            args.storySessionStore.appendEntityStateUpdates(
              sessionId,
              args.currentStory.value?.title ?? '',
              args.selectedWorldId.value,
              event.entity_state_updates,
            )
          } else {
            lastEntityStateUpdates.value = []
          }
          if (event.world_update) {
            lastWorldUpdate.value = event.world_update
            args.storySessionStore.recordWorldUpdate(
              sessionId,
              args.currentStory.value?.title ?? '',
              args.selectedWorldId.value,
              event.world_update,
              new Date().toISOString(),
              event.entity_state_updates?.[0]?.operation_id ?? event.memory_updates?.[0]?.operation_id ?? null,
            )
          } else {
            lastWorldUpdate.value = null
          }
          if (event.story_memory) {
            args.storySessionStore.upsertStoryMemorySession(
              sessionId,
              args.currentStory.value?.title ?? '',
              args.selectedWorldId.value,
              event.story_memory,
            )
          }
          if (event.creation_mode === 'scripted') {
            args.followScriptDesign.value = true
            args.creationMode.value = 'scripted'
            if (args.currentStory.value) args.currentStory.value.metadata.creation_mode = 'scripted'
          }
          if (args.currentStory.value) {
            args.storySessionStore.pushBranchNode(args.currentStory.value.id, {
              nodeId: segment.id,
              parentNodeId,
              prompt,
              contentPreview: segment.content.slice(0, 80),
              choicesOffered: segment.choices,
              chosenIdx: chosenIdx ?? null,
              timestamp: segment.timestamp,
            })
            lastCommittedNodeId.value = segment.id
          }
          generationCompleted = true
        } else if (event.type === 'error') {
          throw new Error(event.message ?? '生成时发生错误')
        }
      }

      await storyLibraryApi.appendSegment(storyId, {
        prompt,
        creation_mode: segment.creation_mode ?? args.creationMode.value,
        content: segment.content,
        retrieved_context: segment.retrieved_context,
        runtime_state_snapshot: segment.runtime_state_snapshot ?? undefined,
      })
    } catch (error: unknown) {
      if (args.currentStory.value) {
        const removableIds = new Set([pendingSegmentId, segment.id])
        args.currentStory.value.segments = args.currentStory.value.segments.filter((item) => !removableIds.has(item.id))
      }
      if ((error as Error)?.name !== 'AbortError') {
        toast({ title: '生成失败', description: (error as Error)?.message, variant: 'destructive' })
      }
    } finally {
      if (generationCompleted) {
        args.clearPromptComposerSelection()
      }
      generating.value = false
      abortController.value = null
      await nextTick()
      scrollToBottom()
    }
  }

  function stopGeneration() {
    abortController.value?.abort()
  }

  async function rollbackLast() {
    if (!args.currentStory.value?.segments.length) return

    const removedSegment = args.currentStory.value.segments[args.currentStory.value.segments.length - 1]
    if (!args.v2SessionId.value) {
      if (removedSegment && args.currentStory.value) {
        args.storySessionStore.rollbackBranchNode(args.currentStory.value.id, removedSegment.id)
        lastCommittedNodeId.value = args.currentStory.value.segments[args.currentStory.value.segments.length - 2]?.id ?? null
      }
      args.currentStory.value.segments.pop()
      if (args.currentStory.value) {
        const rollbackState = await storyLibraryApi.deleteLastSegment(args.currentStory.value.id)
        Object.assign(args.currentStory.value, rollbackState.story)
        if (rollbackState.runtime_state) {
          args.creationMode.value = rollbackState.runtime_state.creation_mode
          args.followScriptDesign.value = rollbackState.runtime_state.creation_mode === 'scripted'
          applyRuntimeSnapshot(rollbackState.runtime_state)
        }
        const entitySnapshot = await storyLibraryApi.getEntityState(args.currentStory.value.id)
        args.storySessionStore.updateEntityStateSnapshot(entitySnapshot)
      }
      return
    }

    try {
      const rollbackResponse = await rollbackLastMessageApi(args.v2SessionId.value)
      if (removedSegment && args.currentStory.value) {
        args.storySessionStore.rollbackBranchNode(args.currentStory.value.id, removedSegment.id)
        const segments = args.currentStory.value.segments
        lastCommittedNodeId.value = segments.length >= 2 ? (segments[segments.length - 2]?.id ?? null) : null
      }
      args.currentStory.value.segments.pop()
      if (args.currentStory.value) {
        const rollbackState = await storyLibraryApi.deleteLastSegment(args.currentStory.value.id)
        Object.assign(args.currentStory.value, rollbackState.story)
        if (rollbackState.runtime_state) {
          args.creationMode.value = rollbackState.runtime_state.creation_mode
          args.followScriptDesign.value = rollbackState.runtime_state.creation_mode === 'scripted'
          applyRuntimeSnapshot(rollbackState.runtime_state)
        }
        const entitySnapshot = await storyLibraryApi.getEntityState(args.currentStory.value.id)
        args.storySessionStore.updateEntityStateSnapshot(entitySnapshot)
      }
      const rollbackEvents = rollbackResponse.memory_updates ?? []
      lastMemoryUpdates.value = rollbackEvents
      lastEntityStateUpdates.value = []
      lastWorldUpdate.value = null
      if (rollbackEvents.length) {
        args.storySessionStore.appendMemoryEvents(
          args.v2SessionId.value,
          args.currentStory.value?.title ?? '',
          args.selectedWorldId.value,
          rollbackEvents,
        )
      }

      const previousSummary = hydrateSummarySnapshotFromStore(
        args.storySessionStore.getSummarySnapshot(args.v2SessionId.value),
        args.v2SessionId.value,
      ) ?? lastSummary.value

      if (rollbackEvents.some((item) => item.memory_layer === 'semantic' && item.action === 'reset')) {
        lastSummaryDiff.value = buildSummaryDiff(previousSummary, null)
        lastSummary.value = null
        args.storySessionStore.removeSummary(args.v2SessionId.value)
      }
      lastContexts.value = extractContextHitsFromUpdates(rollbackEvents)
      toast({ title: '已撤销', description: '最后一轮对话已删除' })
    } catch {
      toast({ title: '撤销失败', variant: 'destructive' })
    }
  }

  async function regenerateLast() {
    if (!args.currentStory.value?.segments.length || generating.value) return
    const lastSegment = args.currentStory.value.segments[args.currentStory.value.segments.length - 1]
    if (!lastSegment) return
    if (!args.v2SessionId.value) {
      await rollbackLast()
      await nextTick()
      await sendPrompt(lastSegment.prompt)
      return
    }

    const storyGenerationModel = args.configStore.getResolvedSceneModel('story_generation')
    generating.value = true

    try {
      const response = await regenerateStoryApi(args.v2SessionId.value, {
        ...(storyGenerationModel.provider
          ? {
              provider: storyGenerationModel.provider,
              base_url: storyGenerationModel.base_url,
            }
          : {}),
        model: storyGenerationModel.model,
        temperature: args.configStore.config.temperature,
        max_tokens: args.configStore.config.maxTokens,
        story_id: args.currentStory.value.id,
        persona_id: args.selectedPersonaId.value || undefined,
        authors_note: args.authorsNote.value || undefined,
        mode: args.storyMode.value,
        instruction: args.storyMode.value === 'instruction' ? (args.instruction.value || undefined) : undefined,
        selected_context_entry_ids: Array.from(
          new Set(
            [
              ...args.selectedContextEntryIds.value,
              ...(args.selectedPrincipalCharacterId.value ? [args.selectedPrincipalCharacterId.value] : []),
            ].filter(Boolean),
          ),
        ),
        script_design_id: args.selectedScriptDesignId.value || undefined,
        active_stage_id: args.selectedScriptStageId.value || undefined,
        active_event_id: args.selectedScriptEventId.value || undefined,
        follow_script_design: args.followScriptDesign.value,
        creation_mode: args.creationMode.value,
        progress_intent: args.progressIntent.value,
        runtime_state_id: args.runtimeStateId.value || undefined,
        allow_state_transition: args.creationMode.value === 'scripted',
        principal_character_id: args.selectedPrincipalCharacterId.value || undefined,
        dialogue_mode: args.dialogueMode.value,
        dialogue_target: args.dialogueTarget.value.trim() || undefined,
        dialogue_intent: args.dialogueIntent.value.trim() || undefined,
        dialogue_style_hint: args.dialogueStyleHint.value.trim() || undefined,
        force_dialogue_round: args.dialogueMode.value === 'required',
        focus_instruction: args.activeFocusTemplate.value?.instruction,
        focus_label: args.activeFocusTemplate.value?.label,
      })

      const previousSummary = hydrateSummarySnapshotFromStore(
        args.storySessionStore.getSummarySnapshot(args.v2SessionId.value),
        args.v2SessionId.value,
      ) ?? lastSummary.value

      lastSegment.content = response.output_text
      lastSegment.choices = response.choices ?? parseChoices(response.output_text)
      lastChoices.value = lastSegment.choices
      if (response.activation_logs?.length) {
        const contextHits = formatActivationHits(response.activation_logs)
        lastSegment.retrieved_context = contextHits.map((item) => `${item.label} · ${item.detail}`)
        lastContexts.value = contextHits
      }
      if (response.memory_updates?.length) {
        lastMemoryUpdates.value = response.memory_updates
        args.storySessionStore.appendMemoryEvents(
          args.v2SessionId.value,
          args.currentStory.value?.title ?? '',
          args.selectedWorldId.value,
          response.memory_updates,
        )
        if (!response.activation_logs?.length) {
          lastContexts.value = extractContextHitsFromUpdates(response.memory_updates)
        }
      } else {
        lastMemoryUpdates.value = []
      }
      if (response.runtime_state_snapshot) {
        lastSegment.runtime_state_snapshot = response.runtime_state_snapshot
        applyRuntimeSnapshot(response.runtime_state_snapshot)
      }
      if (response.entity_state_snapshot) {
        args.storySessionStore.updateEntityStateSnapshot(response.entity_state_snapshot)
      }
      if (response.entity_state_updates?.length) {
        lastEntityStateUpdates.value = response.entity_state_updates
        args.storySessionStore.appendEntityStateUpdates(
          args.v2SessionId.value,
          args.currentStory.value?.title ?? '',
          args.selectedWorldId.value,
          response.entity_state_updates,
        )
      } else {
        lastEntityStateUpdates.value = []
      }
      if (response.world_update) {
        lastWorldUpdate.value = response.world_update
        args.storySessionStore.recordWorldUpdate(
          args.v2SessionId.value,
          args.currentStory.value?.title ?? '',
          args.selectedWorldId.value,
          response.world_update,
          new Date().toISOString(),
          response.entity_state_updates?.[0]?.operation_id ?? response.memory_updates?.[0]?.operation_id ?? null,
        )
      } else {
        lastWorldUpdate.value = null
      }
      if (response.story_memory) {
        args.storySessionStore.upsertStoryMemorySession(
          args.v2SessionId.value,
          args.currentStory.value?.title ?? '',
          args.selectedWorldId.value,
          response.story_memory,
        )
      }
      if (response.creation_mode === 'scripted') {
        args.followScriptDesign.value = true
        args.creationMode.value = 'scripted'
        if (args.currentStory.value) args.currentStory.value.metadata.creation_mode = 'scripted'
      }

      if (response.summary_memory_snapshot) {
        lastSummaryDiff.value = buildSummaryDiff(previousSummary, response.summary_memory_snapshot)
        lastSummary.value = response.summary_memory_snapshot
        args.storySessionStore.updateSummary({
          sessionId: args.v2SessionId.value,
          storyTitle: args.currentStory.value?.title ?? '',
          worldId: args.selectedWorldId.value,
          summary_text: response.summary_memory_snapshot.summary_text,
          key_facts: response.summary_memory_snapshot.key_facts ?? [],
          last_turn: response.summary_memory_snapshot.last_turn ?? 0,
          updatedAt: new Date().toISOString(),
        })
      } else if (response.memory_updates?.some((item) => item.memory_layer === 'semantic' && item.action === 'reset')) {
        lastSummaryDiff.value = buildSummaryDiff(previousSummary, null)
        lastSummary.value = null
        args.storySessionStore.removeSummary(args.v2SessionId.value)
      }

      if (args.currentStory.value) {
        const segments = args.currentStory.value.segments
        lastCommittedNodeId.value = segments[segments.length - 1]?.id ?? null
      }

      toast({ title: '已重生成', description: '最后一轮回复已按当前上下文重建。' })
    } catch (error: unknown) {
      toast({
        title: '重生成失败',
        description: error instanceof Error ? error.message : '无法重生成最后一轮内容',
        variant: 'destructive',
      })
    } finally {
      generating.value = false
      await nextTick()
      scrollToBottom({ force: true })
    }
  }

  function handleBranchSend(payload: { prompt: string; chosenIdx: number }) {
    sendPrompt(payload.prompt, payload.chosenIdx)
  }

  function applySuggestedPrompt(prompt: string) {
    userInput.value = prompt
    clearTemplatePreview()
    clearEnhancementPreview()
    suggestionMenuOpen.value = false
    nextTick(focusInput)
  }

  function previewTemplate(payload: { label: string; prompt: string }) {
    templatePreviewLabel.value = payload.label.trim()
    templatePreviewText.value = payload.prompt.trim()
    suggestionMenuOpen.value = false
  }

  async function requestEnhancedPrompt() {
    const trimmed = userInput.value.trim()
    if (!args.currentStory.value || generating.value || !trimmed) return

    const previewSessionId = args.v2SessionId.value || `story-${args.currentStory.value.id}-v2`
    previewAbortController.value?.abort()
    previewAbortController.value = new AbortController()
    previewLoading.value = true
    previewSourceText.value = trimmed
    const inputEnhancementModel = args.configStore.getResolvedSceneModel('input_enhancement')

    try {
      const preview = await previewEnhancedStoryInput(
        {
          ...(inputEnhancementModel.provider
            ? {
                provider: inputEnhancementModel.provider,
                base_url: inputEnhancementModel.base_url,
              }
            : {}),
          session_id: previewSessionId,
          story_id: args.currentStory.value.id,
          user_input: trimmed,
          world_id: args.selectedWorldId.value || undefined,
          creation_mode: args.creationMode.value,
          progress_intent: args.progressIntent.value,
          runtime_state_id: args.runtimeStateId.value || undefined,
          allow_state_transition: false,
          persona_id: args.selectedPersonaId.value || undefined,
          script_design_id: args.selectedScriptDesignId.value || undefined,
          active_stage_id: args.selectedScriptStageId.value || undefined,
          active_event_id: args.selectedScriptEventId.value || undefined,
          follow_script_design: args.followScriptDesign.value,
          principal_character_id: args.selectedPrincipalCharacterId.value || undefined,
          dialogue_mode: args.dialogueMode.value,
          dialogue_target: args.dialogueTarget.value.trim() || undefined,
          dialogue_intent: args.dialogueIntent.value.trim() || undefined,
          dialogue_style_hint: args.dialogueStyleHint.value.trim() || undefined,
          force_dialogue_round: args.dialogueMode.value === 'required',
          model: inputEnhancementModel.model,
          temperature: args.configStore.config.temperature,
          selected_context_entry_ids: Array.from(
            new Set(
              [
                ...args.selectedContextEntryIds.value,
                ...(args.selectedPrincipalCharacterId.value ? [args.selectedPrincipalCharacterId.value] : []),
              ].filter(Boolean),
            ),
          ),
          focus_instruction: args.activeFocusTemplate.value?.instruction,
          focus_label: args.activeFocusTemplate.value?.label,
        },
        { abortSignal: previewAbortController.value.signal },
      )
      enhancedInputPreview.value = preview.enhanced_text
      previewApplied.value = preview.applied
      previewReason.value = preview.reason ?? null
    } catch (error) {
      if ((error as Error)?.name === 'CanceledError' || (error as Error)?.name === 'AbortError') return
      enhancedInputPreview.value = trimmed
      previewApplied.value = false
      previewReason.value = 'preview_failed'
    } finally {
      previewLoading.value = false
    }
  }

  function applyEnhancedPrompt() {
    if (!enhancedInputPreview.value.trim()) return
    userInput.value = enhancedInputPreview.value.trim()
    clearTemplatePreview()
    clearEnhancementPreview()
    nextTick(focusInput)
  }

  function applyTemplatePreview() {
    if (!templatePreviewText.value.trim()) return
    userInput.value = templatePreviewText.value.trim()
    clearEnhancementPreview()
    clearTemplatePreview()
    nextTick(focusInput)
  }

  onUnmounted(() => {
    abortController.value?.abort()
    clearTemplatePreview()
    clearEnhancementPreview()
  })

  return {
    userInput,
    generating,
    lastChoices,
    lastContexts,
    lastSummary,
    lastMemoryUpdates,
    lastEntityStateUpdates,
    lastWorldUpdate,
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
  }
}
