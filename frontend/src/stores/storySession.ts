/**
 * Story Session Store
 *
 * Tracks summary memory snapshots and branch tree state for story generation.
 *
 * Persistence strategy: same StorageService used by chat/role/config stores.
 * StorageService now writes to the backend SQLite KV endpoint so ALL devices
 * pointing at the same server share the state automatically.
 *
 * Call `loadFromStorage()` once on app mount (App.vue) to hydrate from backend.
 * Subsequent mutations auto-persist via watchers (debounced 300 ms).
 */
import { defineStore } from 'pinia'
import { ref, watch } from 'vue'
import type {
  EntityStateCollection,
  EntityStateUpdate,
  MemoryUpdateEvent,
  StoryMemoryPayload,
} from '@/domains/story/api/storyGenerationApi'
import {
  deriveSummaryLifecycleState,
  type SummaryLifecycleState,
} from '@/domains/memory/memoryUpdatePresentation'
import { storage } from '@/utils/storage'

export interface StorySummaryRecord {
  sessionId: string
  storyTitle: string
  worldId: string
  summary_text: string
  key_facts: string[]
  last_turn: number
  updatedAt: string
}

export interface StoryMemoryEventRecord {
  eventId: string
  sessionId: string
  operationId: string | null
  sequence: number | null
  displayKind: string | null
  storyTitle: string
  worldId: string
  memoryLayer: string
  action: string
  source: string
  sourceTurn: number | null
  memoryKey: string | null
  title: string
  reason: string | null
  before: Record<string, unknown> | null
  after: Record<string, unknown> | null
  status: string
  committedAt: string
}

export interface StoryEntityUpdateRecord {
  eventId: string
  sessionId: string
  storyTitle: string
  worldId: string
  storyId: string
  entityId: string
  entityType: 'character'
  entityName: string | null
  fieldName: string
  op: string
  value: unknown
  before: unknown
  after: unknown
  evidenceText: string | null
  sourceTurn: number | null
  source: string
  operationId: string | null
  sequence: number | null
  confidence: number | null
  status: string
  committedAt: string
  metadata: Record<string, unknown>
}

export interface StoryWorldUpdateRecord {
  sessionId: string
  storyTitle: string
  worldId: string
  operationId: string | null
  updatedAt: string
  payload: Record<string, unknown>
}

export interface StoryMemorySessionRecord {
  sessionId: string
  storyTitle: string
  worldId: string
  updatedAt: string
  storyMemory: StoryMemoryPayload
}

// ── Branch Tree Types ────────────────────────────────────────────────────────

/** A single node in the story exploration tree */
export interface BranchNode {
  /** Matches the corresponding StorySegment.id */
  nodeId: string
  parentNodeId: string | null
  /** The user prompt that triggered this node */
  prompt: string
  /** First ~80 chars of AI response for tooltip/preview */
  contentPreview: string
  /** The raw choices array AI returned, if any */
  choicesOffered: string[]
  /** Which choice index was selected (null = free-form input) */
  chosenIdx: number | null
  timestamp: string
  /** Set to false when the user rolls back past this node */
  isOnActivePath: boolean
}

export interface StoryBranchTree {
  storyId: string
  /** nodeId → BranchNode */
  nodes: Record<string, BranchNode>
  rootNodeId: string | null
  activeNodeId: string | null
}

// useStorySessionStore 状态仓库实例。
export const useStorySessionStore = defineStore('storySession', () => {
  // ── Storage keys ─────────────────────────────────────────────────────────
  const STORAGE_KEYS = {
    summaryMap: 'story-summary-map',
    memoryEvents: 'story-memory-events',
    entityStates: 'story-entity-state-map',
    entityUpdates: 'story-entity-update-map',
    worldUpdates: 'story-world-update-map',
    storyMemorySessions: 'story-memory-session-map',
    runtimeSummaryStates: 'story-runtime-summary-states',
    branchTrees: 'story-branch-trees',
  } as const

  // ── Reactive state (pure refs — loaded via loadFromStorage on mount) ──────
  const summaryMap  = ref<Record<string, StorySummaryRecord>>({})
  const runtimeMemoryEventsBySession = ref<Record<string, StoryMemoryEventRecord[]>>({})
  const entityStateMap = ref<Record<string, EntityStateCollection>>({})
  const entityUpdateMap = ref<Record<string, StoryEntityUpdateRecord[]>>({})
  const worldUpdateMap = ref<Record<string, StoryWorldUpdateRecord>>({})
  const storyMemorySessionMap = ref<Record<string, StoryMemorySessionRecord>>({})
  const memoryEventMap = runtimeMemoryEventsBySession
  const runtimeSummaryStateBySession = ref<Record<string, SummaryLifecycleState>>({})
  const branchTrees = ref<Record<string, StoryBranchTree>>({})

  /** Prevents watchers from writing empty state before loadFromStorage finishes */
  const _loaded = ref(false)

  // ── Persistence ───────────────────────────────────────────────────────────

  /**
   * Load state from StorageService.
   * - Fast path: data already in localStorage → use it immediately
   * - New-device path: localStorage empty → pull from backend (cross-device sync)
   * Call once in App.vue `onMounted`.
   */
  async function loadFromStorage() {
    let summaryRaw  = await storage.getStorage(STORAGE_KEYS.summaryMap)
    let eventsRaw   = await storage.getStorage(STORAGE_KEYS.memoryEvents)
    let entityStatesRaw = await storage.getStorage(STORAGE_KEYS.entityStates)
    let entityUpdatesRaw = await storage.getStorage(STORAGE_KEYS.entityUpdates)
    let worldUpdatesRaw = await storage.getStorage(STORAGE_KEYS.worldUpdates)
    let storyMemorySessionsRaw = await storage.getStorage(STORAGE_KEYS.storyMemorySessions)
    let runtimeSummaryStatesRaw = await storage.getStorage(STORAGE_KEYS.runtimeSummaryStates)
    let treesRaw    = await storage.getStorage(STORAGE_KEYS.branchTrees)

    // New device: localStorage has nothing → try pulling from backend
    if (!summaryRaw)  summaryRaw  = await storage.pullFromRemote(STORAGE_KEYS.summaryMap)
    if (!eventsRaw)   eventsRaw   = await storage.pullFromRemote(STORAGE_KEYS.memoryEvents)
    if (!entityStatesRaw) entityStatesRaw = await storage.pullFromRemote(STORAGE_KEYS.entityStates)
    if (!entityUpdatesRaw) entityUpdatesRaw = await storage.pullFromRemote(STORAGE_KEYS.entityUpdates)
    if (!worldUpdatesRaw) worldUpdatesRaw = await storage.pullFromRemote(STORAGE_KEYS.worldUpdates)
    if (!storyMemorySessionsRaw) storyMemorySessionsRaw = await storage.pullFromRemote(STORAGE_KEYS.storyMemorySessions)
    if (!runtimeSummaryStatesRaw) runtimeSummaryStatesRaw = await storage.pullFromRemote(STORAGE_KEYS.runtimeSummaryStates)
    if (!treesRaw)    treesRaw    = await storage.pullFromRemote(STORAGE_KEYS.branchTrees)

    if (summaryRaw) {
      try { summaryMap.value  = JSON.parse(summaryRaw)  } catch { /* corrupt */ }
    }
    if (eventsRaw) {
      try { runtimeMemoryEventsBySession.value = JSON.parse(eventsRaw) } catch { /* corrupt */ }
    }
    if (entityStatesRaw) {
      try { entityStateMap.value = JSON.parse(entityStatesRaw) } catch { /* corrupt */ }
    }
    if (entityUpdatesRaw) {
      try { entityUpdateMap.value = JSON.parse(entityUpdatesRaw) } catch { /* corrupt */ }
    }
    if (worldUpdatesRaw) {
      try { worldUpdateMap.value = JSON.parse(worldUpdatesRaw) } catch { /* corrupt */ }
    }
    if (storyMemorySessionsRaw) {
      try { storyMemorySessionMap.value = JSON.parse(storyMemorySessionsRaw) } catch { /* corrupt */ }
    }
    if (runtimeSummaryStatesRaw) {
      try { runtimeSummaryStateBySession.value = JSON.parse(runtimeSummaryStatesRaw) } catch { /* corrupt */ }
    }
    if (treesRaw) {
      try { branchTrees.value = JSON.parse(treesRaw)    } catch { /* corrupt */ }
    }
    Object.keys(summaryMap.value).forEach((sessionId) => syncRuntimeSummaryState(sessionId))
    Object.keys(runtimeMemoryEventsBySession.value).forEach((sessionId) => syncRuntimeSummaryState(sessionId))
    const allStoryMemorySessionIds = new Set([
      ...Object.keys(summaryMap.value),
      ...Object.keys(runtimeMemoryEventsBySession.value),
      ...Object.keys(entityStateMap.value),
      ...Object.keys(entityUpdateMap.value),
      ...Object.keys(worldUpdateMap.value),
      ...Object.keys(storyMemorySessionMap.value),
    ])
    Array.from(allStoryMemorySessionIds).forEach((sessionId) => syncStoryMemorySession(sessionId))
    _loaded.value = true
  }

  async function _persistSummary() {
    if (!_loaded.value) return
    await storage.setStorage(STORAGE_KEYS.summaryMap, JSON.stringify(summaryMap.value))
  }

  async function _persistEvents() {
    if (!_loaded.value) return
    await storage.setStorage(STORAGE_KEYS.memoryEvents, JSON.stringify(runtimeMemoryEventsBySession.value))
  }

  async function _persistEntityStates() {
    if (!_loaded.value) return
    await storage.setStorage(STORAGE_KEYS.entityStates, JSON.stringify(entityStateMap.value))
  }

  async function _persistEntityUpdates() {
    if (!_loaded.value) return
    await storage.setStorage(STORAGE_KEYS.entityUpdates, JSON.stringify(entityUpdateMap.value))
  }

  async function _persistWorldUpdates() {
    if (!_loaded.value) return
    await storage.setStorage(STORAGE_KEYS.worldUpdates, JSON.stringify(worldUpdateMap.value))
  }

  async function _persistStoryMemorySessions() {
    if (!_loaded.value) return
    await storage.setStorage(STORAGE_KEYS.storyMemorySessions, JSON.stringify(storyMemorySessionMap.value))
  }

  async function _persistRuntimeSummaryStates() {
    if (!_loaded.value) return
    await storage.setStorage(STORAGE_KEYS.runtimeSummaryStates, JSON.stringify(runtimeSummaryStateBySession.value))
  }

  async function _persistTrees() {
    if (!_loaded.value) return
    await storage.setStorage(STORAGE_KEYS.branchTrees, JSON.stringify(branchTrees.value))
  }

  // Auto-persist on every mutation (debounced 300 ms to batch rapid changes)
  let _summaryTimer: ReturnType<typeof setTimeout> | null = null
  let _eventsTimer:  ReturnType<typeof setTimeout> | null = null
  let _entityStatesTimer: ReturnType<typeof setTimeout> | null = null
  let _entityUpdatesTimer: ReturnType<typeof setTimeout> | null = null
  let _worldUpdatesTimer: ReturnType<typeof setTimeout> | null = null
  let _storyMemorySessionsTimer: ReturnType<typeof setTimeout> | null = null
  let _runtimeSummaryStateTimer: ReturnType<typeof setTimeout> | null = null
  let _treesTimer:   ReturnType<typeof setTimeout> | null = null

  watch(summaryMap, () => {
    if (_summaryTimer) clearTimeout(_summaryTimer)
    _summaryTimer = setTimeout(_persistSummary, 300)
  }, { deep: true })

  watch(runtimeMemoryEventsBySession, () => {
    if (_eventsTimer) clearTimeout(_eventsTimer)
    _eventsTimer = setTimeout(_persistEvents, 300)
  }, { deep: true })

  watch(entityStateMap, () => {
    if (_entityStatesTimer) clearTimeout(_entityStatesTimer)
    _entityStatesTimer = setTimeout(_persistEntityStates, 300)
  }, { deep: true })

  watch(entityUpdateMap, () => {
    if (_entityUpdatesTimer) clearTimeout(_entityUpdatesTimer)
    _entityUpdatesTimer = setTimeout(_persistEntityUpdates, 300)
  }, { deep: true })

  watch(worldUpdateMap, () => {
    if (_worldUpdatesTimer) clearTimeout(_worldUpdatesTimer)
    _worldUpdatesTimer = setTimeout(_persistWorldUpdates, 300)
  }, { deep: true })

  watch(storyMemorySessionMap, () => {
    if (_storyMemorySessionsTimer) clearTimeout(_storyMemorySessionsTimer)
    _storyMemorySessionsTimer = setTimeout(_persistStoryMemorySessions, 300)
  }, { deep: true })

  watch(runtimeSummaryStateBySession, () => {
    if (_runtimeSummaryStateTimer) clearTimeout(_runtimeSummaryStateTimer)
    _runtimeSummaryStateTimer = setTimeout(_persistRuntimeSummaryStates, 300)
  }, { deep: true })

  watch(branchTrees, () => {
    if (_treesTimer) clearTimeout(_treesTimer)
    _treesTimer = setTimeout(_persistTrees, 300)
  }, { deep: true })

  // ── Summary helpers ───────────────────────────────────────────────────────
  function getSummarySnapshot(sessionId: string) {
    const storyMemorySummary = storyMemorySessionMap.value[sessionId]?.storyMemory?.semantic?.summary_memory_snapshot
    if (storyMemorySummary) {
      return {
        summary_text: storyMemorySummary.summary_text,
        key_facts: storyMemorySummary.key_facts ?? [],
        last_turn: storyMemorySummary.last_turn ?? 0,
        session_id: storyMemorySummary.session_id ?? sessionId,
      }
    }
    const record = summaryMap.value[sessionId]
    if (!record) return null
    return {
      summary_text: record.summary_text,
      key_facts: record.key_facts,
      last_turn: record.last_turn,
      session_id: sessionId,
    }
  }

  function buildStoryMemoryPayload(
    sessionId: string,
    worldIdOverride?: string,
  ): StoryMemoryPayload {
    const summaryRecord = summaryMap.value[sessionId]
    const summarySnapshot = summaryRecord
      ? {
          summary_text: summaryRecord.summary_text,
          key_facts: summaryRecord.key_facts,
          last_turn: summaryRecord.last_turn,
          session_id: sessionId,
        }
      : null
    const entitySnapshot = entityStateMap.value[sessionId] ?? null
    const entityUpdates = [...(entityUpdateMap.value[sessionId] ?? [])]
      .sort((a, b) => {
        const timeCompare = b.committedAt.localeCompare(a.committedAt)
        if (timeCompare !== 0) return timeCompare
        return (b.sequence ?? 0) - (a.sequence ?? 0)
      })
      .slice(0, 120)
    const memoryEvents = [...(runtimeMemoryEventsBySession.value[sessionId] ?? [])]
      .sort((a, b) => b.committedAt.localeCompare(a.committedAt))
      .slice(0, 50)
    const worldUpdate = worldUpdateMap.value[sessionId] ?? null
    const operationId = entityUpdates[0]?.operationId
      ?? memoryEvents[0]?.operationId
      ?? worldUpdate?.operationId
      ?? null
    const committedAt = entityUpdates[0]?.committedAt
      ?? memoryEvents[0]?.committedAt
      ?? worldUpdate?.updatedAt
      ?? summaryMap.value[sessionId]?.updatedAt
      ?? new Date().toISOString()
    const statuses = [...memoryEvents.map((item) => item.status), ...entityUpdates.map((item) => item.status)]
    const status = statuses.includes('failed')
      ? 'failed'
      : statuses.includes('stale')
        ? 'stale'
        : 'committed'
    const sequences = [...memoryEvents.map((item) => item.sequence), ...entityUpdates.map((item) => item.sequence)]
      .filter((item): item is number => typeof item === 'number')
    return {
      session_id: sessionId,
      story_id: entityUpdates[0]?.storyId ?? entitySnapshot?.story_id ?? null,
      world_id: worldIdOverride
        ?? summaryMap.value[sessionId]?.worldId
        ?? worldUpdate?.worldId
        ?? null,
      operation: {
        operation_id: operationId,
        source: entityUpdates[0]?.source ?? memoryEvents[0]?.source ?? null,
        status,
        committed_at: committedAt,
        sequence_min: sequences.length ? Math.min(...sequences) : null,
        sequence_max: sequences.length ? Math.max(...sequences) : null,
        event_count: memoryEvents.length,
        entity_update_count: entityUpdates.length,
      },
      semantic: {
        summary_memory_snapshot: summarySnapshot,
      },
      runtime: {
        runtime_state_snapshot: null,
      },
      entity: {
        entity_state_snapshot: entitySnapshot,
        entity_state_updates: entityUpdates.map((item) => ({
          event_id: item.eventId,
          story_id: item.storyId,
          session_id: item.sessionId,
          entity_id: item.entityId,
          entity_type: item.entityType,
          entity_name: item.entityName,
          field_name: item.fieldName,
          op: item.op,
          value: item.value,
          before: item.before,
          after: item.after,
          evidence_text: item.evidenceText,
          source_turn: item.sourceTurn,
          source: item.source,
          operation_id: item.operationId,
          sequence: item.sequence,
          confidence: item.confidence,
          status: item.status,
          committed_at: item.committedAt,
          metadata: item.metadata,
        })),
        world_update: worldUpdate?.payload ?? null,
      },
      timeline: {
        memory_updates: memoryEvents.map((item) => ({
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
        })),
      },
    }
  }

  function syncStoryMemorySession(
    sessionId: string,
    storyTitle?: string,
    worldId?: string,
  ) {
    const currentTitle = storyTitle
      ?? summaryMap.value[sessionId]?.storyTitle
      ?? worldUpdateMap.value[sessionId]?.storyTitle
      ?? storyMemorySessionMap.value[sessionId]?.storyTitle
      ?? ''
    const currentWorldId = worldId
      ?? summaryMap.value[sessionId]?.worldId
      ?? worldUpdateMap.value[sessionId]?.worldId
      ?? storyMemorySessionMap.value[sessionId]?.worldId
      ?? ''
    storyMemorySessionMap.value[sessionId] = {
      sessionId,
      storyTitle: currentTitle,
      worldId: currentWorldId,
      updatedAt: new Date().toISOString(),
      storyMemory: buildStoryMemoryPayload(sessionId, currentWorldId),
    }
  }

  function getStoryMemorySession(sessionId: string): StoryMemorySessionRecord | null {
    return storyMemorySessionMap.value[sessionId] ?? null
  }

  function getAllStoryMemorySessions(): StoryMemorySessionRecord[] {
    return Object.values(storyMemorySessionMap.value).sort((left, right) => (
      right.updatedAt.localeCompare(left.updatedAt)
    ))
  }

  function upsertStoryMemorySession(
    sessionId: string,
    storyTitle: string,
    worldId: string,
    storyMemory: StoryMemoryPayload,
  ) {
    storyMemorySessionMap.value[sessionId] = {
      sessionId,
      storyTitle: storyTitle || storyMemorySessionMap.value[sessionId]?.storyTitle || '',
      worldId: storyMemory.world_id ?? worldId ?? storyMemorySessionMap.value[sessionId]?.worldId ?? '',
      updatedAt: storyMemory.operation?.committed_at ?? new Date().toISOString(),
      storyMemory: {
        ...storyMemory,
        session_id: storyMemory.session_id || sessionId,
        world_id: storyMemory.world_id ?? worldId ?? null,
      },
    }
  }

  function updateEntityStateSnapshot(snapshot: EntityStateCollection) {
    entityStateMap.value[snapshot.session_id] = {
      ...snapshot,
      items: snapshot.items.map((item) => ({
        ...item,
        inventory: [...item.inventory],
        status_tags: [...item.status_tags],
        companions: item.companions.map((companion) => (
          typeof companion === 'string'
            ? companion
            : { ...companion }
        )),
        evidence: [...item.evidence],
        metadata: { ...item.metadata },
      })),
    }
    syncStoryMemorySession(snapshot.session_id)
  }

  function getEntityStateSnapshot(sessionId: string): EntityStateCollection | null {
    const storyMemorySnapshot = storyMemorySessionMap.value[sessionId]?.storyMemory?.entity?.entity_state_snapshot
    if (storyMemorySnapshot) return storyMemorySnapshot
    return entityStateMap.value[sessionId] ?? null
  }

  function removeEntityStateSnapshot(sessionId: string) {
    delete entityStateMap.value[sessionId]
    syncStoryMemorySession(sessionId)
  }

  function appendEntityStateUpdates(
    sessionId: string,
    storyTitle: string,
    worldId: string,
    updates: EntityStateUpdate[],
  ) {
    if (!updates.length) return
    const existing = entityUpdateMap.value[sessionId] ?? []
    const normalized = updates.map((update) => ({
      eventId: update.event_id,
      sessionId,
      storyTitle,
      worldId,
      storyId: update.story_id,
      entityId: update.entity_id,
      entityType: update.entity_type,
      entityName: update.entity_name ?? null,
      fieldName: update.field_name,
      op: update.op,
      value: update.value ?? null,
      before: update.before ?? null,
      after: update.after ?? null,
      evidenceText: update.evidence_text ?? null,
      sourceTurn: update.source_turn ?? null,
      source: update.source,
      operationId: update.operation_id ?? null,
      sequence: update.sequence ?? null,
      confidence: update.confidence ?? null,
      status: update.status,
      committedAt: update.committed_at,
      metadata: { ...(update.metadata ?? {}) },
    }))
    const merged = [...normalized, ...existing]
    const deduped = Array.from(new Map(merged.map((item) => [item.eventId, item])).values())
    deduped.sort((a, b) => {
      const timeCompare = b.committedAt.localeCompare(a.committedAt)
      if (timeCompare !== 0) return timeCompare
      return (b.sequence ?? 0) - (a.sequence ?? 0)
    })
    entityUpdateMap.value[sessionId] = deduped.slice(0, 120)
    syncStoryMemorySession(sessionId, storyTitle, worldId)
  }

  function getSessionEntityStateUpdates(sessionId: string, limit = 30): StoryEntityUpdateRecord[] {
    const storyMemoryUpdates = storyMemorySessionMap.value[sessionId]?.storyMemory?.entity?.entity_state_updates ?? []
    if (storyMemoryUpdates.length) {
      return [...storyMemoryUpdates]
        .map((update) => ({
          eventId: update.event_id,
          sessionId,
          storyTitle: storyMemorySessionMap.value[sessionId]?.storyTitle ?? '',
          worldId: storyMemorySessionMap.value[sessionId]?.worldId ?? '',
          storyId: update.story_id,
          entityId: update.entity_id,
          entityType: update.entity_type,
          entityName: update.entity_name ?? null,
          fieldName: update.field_name,
          op: update.op,
          value: update.value ?? null,
          before: update.before ?? null,
          after: update.after ?? null,
          evidenceText: update.evidence_text ?? null,
          sourceTurn: update.source_turn ?? null,
          source: update.source,
          operationId: update.operation_id ?? null,
          sequence: update.sequence ?? null,
          confidence: update.confidence ?? null,
          status: update.status,
          committedAt: update.committed_at,
          metadata: { ...(update.metadata ?? {}) },
        }))
        .sort((a, b) => {
          const timeCompare = b.committedAt.localeCompare(a.committedAt)
          if (timeCompare !== 0) return timeCompare
          return (b.sequence ?? 0) - (a.sequence ?? 0)
        })
        .slice(0, limit)
    }
    return [...(entityUpdateMap.value[sessionId] ?? [])]
      .sort((a, b) => {
        const timeCompare = b.committedAt.localeCompare(a.committedAt)
        if (timeCompare !== 0) return timeCompare
        return (b.sequence ?? 0) - (a.sequence ?? 0)
      })
      .slice(0, limit)
  }

  function recordWorldUpdate(
    sessionId: string,
    storyTitle: string,
    worldId: string,
    payload: Record<string, unknown> | null | undefined,
    updatedAt?: string,
    operationId?: string | null,
  ) {
    if (!payload) return
    worldUpdateMap.value[sessionId] = {
      sessionId,
      storyTitle,
      worldId,
      operationId: operationId ?? null,
      updatedAt: updatedAt ?? new Date().toISOString(),
      payload: { ...payload },
    }
    syncStoryMemorySession(sessionId, storyTitle, worldId)
  }

  function getSessionWorldUpdate(sessionId: string): StoryWorldUpdateRecord | null {
    const storyMemoryWorldUpdate = storyMemorySessionMap.value[sessionId]?.storyMemory?.entity?.world_update
    if (storyMemoryWorldUpdate) {
      return {
        sessionId,
        storyTitle: storyMemorySessionMap.value[sessionId]?.storyTitle ?? '',
        worldId: storyMemorySessionMap.value[sessionId]?.worldId ?? '',
        operationId: storyMemorySessionMap.value[sessionId]?.storyMemory?.operation?.operation_id ?? null,
        updatedAt: storyMemorySessionMap.value[sessionId]?.storyMemory?.operation?.committed_at ?? new Date().toISOString(),
        payload: { ...storyMemoryWorldUpdate },
      }
    }
    return worldUpdateMap.value[sessionId] ?? null
  }

  function syncRuntimeSummaryState(sessionId: string) {
    runtimeSummaryStateBySession.value[sessionId] = deriveSummaryLifecycleState(
      (runtimeMemoryEventsBySession.value[sessionId] ?? []).map((event) => ({
        memory_layer: event.memoryLayer,
        action: event.action,
        status: event.status,
        committed_at: event.committedAt,
      })),
      getSummarySnapshot(sessionId),
    )
  }

  function updateSummary(record: StorySummaryRecord) {
    summaryMap.value[record.sessionId] = { ...record }
    syncRuntimeSummaryState(record.sessionId)
    syncStoryMemorySession(record.sessionId, record.storyTitle, record.worldId)
  }

  function appendMemoryEvents(
    sessionId: string,
    storyTitle: string,
    worldId: string,
    events: MemoryUpdateEvent[],
  ) {
    if (!events.length) return
    const existing = runtimeMemoryEventsBySession.value[sessionId] ?? []
    const normalized = events.map((event) => ({
      eventId: event.event_id,
      sessionId,
      operationId: event.operation_id ?? null,
      sequence: event.sequence ?? null,
      displayKind: event.display_kind ?? null,
      storyTitle,
      worldId,
      memoryLayer: event.memory_layer,
      action: event.action,
      source: event.source,
      sourceTurn: event.source_turn ?? null,
      memoryKey: event.memory_key ?? null,
      title: event.title,
      reason: event.reason ?? null,
      before: event.before ?? null,
      after: event.after ?? null,
      status: event.status ?? 'committed',
      committedAt: event.committed_at,
    }))
    const merged = [...normalized, ...existing]
    const deduped = Array.from(new Map(merged.map((item) => [item.eventId, item])).values())
    deduped.sort((a, b) => b.committedAt.localeCompare(a.committedAt))
    runtimeMemoryEventsBySession.value[sessionId] = deduped.slice(0, 50)
    syncRuntimeSummaryState(sessionId)
    syncStoryMemorySession(sessionId, storyTitle, worldId)
  }

  function getAllSummaries(): StorySummaryRecord[] {
    return Object.values(summaryMap.value).sort(
      (a, b) => b.updatedAt.localeCompare(a.updatedAt),
    )
  }

  function getRecentMemoryEvents(limit = 20): StoryMemoryEventRecord[] {
    return Object.values(runtimeMemoryEventsBySession.value)
      .flat()
      .sort((a, b) => b.committedAt.localeCompare(a.committedAt))
      .slice(0, limit)
  }

  function getSessionMemoryEvents(sessionId: string, limit = 20): StoryMemoryEventRecord[] {
    const storyMemoryEvents = storyMemorySessionMap.value[sessionId]?.storyMemory?.timeline?.memory_updates ?? []
    if (storyMemoryEvents.length) {
      return [...storyMemoryEvents]
        .map((event) => ({
          eventId: event.event_id,
          sessionId,
          operationId: event.operation_id ?? null,
          sequence: event.sequence ?? null,
          displayKind: event.display_kind ?? null,
          storyTitle: storyMemorySessionMap.value[sessionId]?.storyTitle ?? '',
          worldId: storyMemorySessionMap.value[sessionId]?.worldId ?? '',
          memoryLayer: event.memory_layer,
          action: event.action,
          source: event.source,
          sourceTurn: event.source_turn ?? null,
          memoryKey: event.memory_key ?? null,
          title: event.title,
          reason: event.reason ?? null,
          before: event.before ?? null,
          after: event.after ?? null,
          status: event.status ?? 'committed',
          committedAt: event.committed_at,
        }))
        .sort((a, b) => b.committedAt.localeCompare(a.committedAt))
        .slice(0, limit)
    }
    return [...(runtimeMemoryEventsBySession.value[sessionId] ?? [])]
      .sort((a, b) => b.committedAt.localeCompare(a.committedAt))
      .slice(0, limit)
  }

  function getRuntimeSummaryState(sessionId: string): SummaryLifecycleState {
    return runtimeSummaryStateBySession.value[sessionId]
      ?? deriveSummaryLifecycleState(
        (runtimeMemoryEventsBySession.value[sessionId] ?? []).map((event) => ({
          memory_layer: event.memoryLayer,
          action: event.action,
          status: event.status,
          committed_at: event.committedAt,
        })),
        getSummarySnapshot(sessionId),
      )
  }

  function removeSummary(sessionId: string) {
    delete summaryMap.value[sessionId]
    syncRuntimeSummaryState(sessionId)
    syncStoryMemorySession(sessionId)
  }

  async function clearAll() {
    summaryMap.value  = {}
    runtimeMemoryEventsBySession.value = {}
    entityStateMap.value = {}
    entityUpdateMap.value = {}
    worldUpdateMap.value = {}
    storyMemorySessionMap.value = {}
    runtimeSummaryStateBySession.value = {}
    branchTrees.value = {}
    await Promise.all([
      storage.deleteStorage(STORAGE_KEYS.summaryMap),
      storage.deleteStorage(STORAGE_KEYS.memoryEvents),
      storage.deleteStorage(STORAGE_KEYS.entityStates),
      storage.deleteStorage(STORAGE_KEYS.entityUpdates),
      storage.deleteStorage(STORAGE_KEYS.worldUpdates),
      storage.deleteStorage(STORAGE_KEYS.storyMemorySessions),
      storage.deleteStorage(STORAGE_KEYS.runtimeSummaryStates),
      storage.deleteStorage(STORAGE_KEYS.branchTrees),
    ])
  }

  // ── Branch tree helpers ───────────────────────────────────────────────────

  function getOrCreateTree(storyId: string): StoryBranchTree {
    if (!branchTrees.value[storyId]) {
      branchTrees.value[storyId] = {
        storyId,
        nodes: {},
        rootNodeId: null,
        activeNodeId: null,
      }
    }
    return branchTrees.value[storyId]!
  }

  /**
   * Call this after AI response arrives to register the node in the tree.
   * parentNodeId = null for the first segment.
   */
  function pushBranchNode(
    storyId: string,
    node: Omit<BranchNode, 'isOnActivePath'>,
  ) {
    const tree = getOrCreateTree(storyId)
    tree.nodes[node.nodeId] = { ...node, isOnActivePath: true }
    if (tree.rootNodeId === null) tree.rootNodeId = node.nodeId
    tree.activeNodeId = node.nodeId
  }

  /**
   * Call this when the user rolls back the last segment.
   * Marks the removed node as off the active path and resets activeNodeId.
   */
  function rollbackBranchNode(storyId: string, removedNodeId: string) {
    const tree = branchTrees.value[storyId]
    if (!tree) return
    const node = tree.nodes[removedNodeId]
    if (node) node.isOnActivePath = false
    tree.activeNodeId = node?.parentNodeId ?? null
  }

  function getBranchTree(storyId: string): StoryBranchTree | undefined {
    return branchTrees.value[storyId]
  }

  /** Build a structure suitable for ECharts tree rendering */
  function buildEChartsTree(storyId: string): Record<string, unknown> | null {
    const tree = branchTrees.value[storyId]
    if (!tree || !tree.rootNodeId) return null

    function toNode(nodeId: string): Record<string, unknown> {
      const n = tree!.nodes[nodeId]
      if (!n) return { name: nodeId, children: undefined }

      const children = Object.values(tree!.nodes)
        .filter(child => child.parentNodeId === nodeId)
        .map(child => toNode(child.nodeId))

      const label = n.prompt.length > 20 ? n.prompt.slice(0, 20) + '…' : n.prompt

      return {
        name: label,
        nodeId,
        chosenIdx: n.chosenIdx,
        isOnActivePath: n.isOnActivePath,
        isActive: nodeId === tree!.activeNodeId,
        contentPreview: n.contentPreview,
        prompt: n.prompt,
        children: children.length ? children : undefined,
        itemStyle: {
          color: nodeId === tree!.activeNodeId
            ? '#f97316'                   // active: orange
            : n.isOnActivePath
              ? '#3b82f6'                 // on-path: blue
              : '#94a3b8',               // off-path: slate
          borderColor: nodeId === tree!.activeNodeId ? '#ea580c' : undefined,
          borderWidth: nodeId === tree!.activeNodeId ? 2 : 0,
        },
        label: {
          color: n.isOnActivePath ? '#e2e8f0' : '#94a3b8',
        },
      }
    }

    return toNode(tree.rootNodeId)
  }

  return {
    loadFromStorage,
    updateSummary,
    updateEntityStateSnapshot,
    appendEntityStateUpdates,
    appendMemoryEvents,
    getAllSummaries,
    getSummarySnapshot,
    getRecentMemoryEvents,
    getSessionMemoryEvents,
    getEntityStateSnapshot,
    getSessionEntityStateUpdates,
    getSessionWorldUpdate,
    getStoryMemorySession,
    getAllStoryMemorySessions,
    upsertStoryMemorySession,
    getRuntimeSummaryState,
    recordWorldUpdate,
    removeSummary,
    removeEntityStateSnapshot,
    clearAll,
    pushBranchNode,
    rollbackBranchNode,
    getBranchTree,
    buildEChartsTree,
  }
})
