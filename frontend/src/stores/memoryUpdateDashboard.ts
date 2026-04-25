/**
 * 文件说明：前端状态管理与会话数据维护。
 */

import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import type {
  MemorySessionTimelineResponse,
  MemoryUpdateQueryFilters,
  MemoryUpdateQueryResponse,
  StoryMemorySnapshotResponse,
} from '@/domains/memory/api/memoryUpdatesApi'

export type MemoryUpdateDetailTab = 'timeline' | 'semantic' | 'entity'
export type MemorySessionViewMode = 'all' | 'attention' | 'tracked' | 'summarized'

// useMemoryUpdateDashboardStore 状态仓库实例。
export const useMemoryUpdateDashboardStore = defineStore('memoryUpdateDashboard', () => {
  const searchTerm = ref('')
  const sessionSearchTerm = ref('')
  const selectedSource = ref('all')
  const selectedLayer = ref('all')
  const selectedStatus = ref('all')
  const sessionViewMode = ref<MemorySessionViewMode>('all')
  const selectedSessionId = ref<string | null>(null)
  const sessionListPage = ref(1)
  const sessionListPageSize = ref(6)
  const detailPage = ref(1)
  const detailPageSize = ref(100)
  const detailTab = ref<MemoryUpdateDetailTab>('timeline')

  const listSnapshot = ref<MemoryUpdateQueryResponse | null>(null)
  const timelineSnapshotBySession = ref<Record<string, MemorySessionTimelineResponse>>({})
  const storyMemorySnapshotBySession = ref<Record<string, StoryMemorySnapshotResponse>>({})

  const queryFilters = computed<MemoryUpdateQueryFilters>(() => {
    return {
      search: searchTerm.value.trim() || undefined,
      source: selectedSource.value === 'all' ? undefined : selectedSource.value,
      memory_layer: selectedLayer.value === 'all' ? undefined : selectedLayer.value,
      status: selectedStatus.value === 'all' ? undefined : selectedStatus.value,
      page: 1,
      page_size: 120,
    }
  })

  function setSearchTerm(value: string) {
    searchTerm.value = value
  }

  function setSessionSearchTerm(value: string) {
    sessionSearchTerm.value = value
  }

  function setSelectedSource(value: string) {
    selectedSource.value = value
  }

  function setSelectedLayer(value: string) {
    selectedLayer.value = value
  }

  function setSelectedStatus(value: string) {
    selectedStatus.value = value
  }

  function setSessionViewMode(value: MemorySessionViewMode) {
    sessionViewMode.value = value
  }

  function setSelectedSessionId(value: string | null) {
    selectedSessionId.value = value
  }

  function setSessionListPage(value: number) {
    sessionListPage.value = Math.max(1, value)
  }

  function setSessionListPageSize(value: number) {
    sessionListPageSize.value = Math.max(1, value)
  }

  function setDetailPage(value: number) {
    detailPage.value = Math.max(1, value)
  }

  function setDetailPageSize(value: number) {
    detailPageSize.value = Math.max(1, value)
  }

  function setDetailTab(value: MemoryUpdateDetailTab) {
    detailTab.value = value
  }

  function setListSnapshot(value: MemoryUpdateQueryResponse | null | undefined) {
    listSnapshot.value = value ?? null
  }

  function setTimelineSnapshot(sessionId: string, value: MemorySessionTimelineResponse | null | undefined) {
    if (!sessionId) return
    if (!value) {
      delete timelineSnapshotBySession.value[sessionId]
      return
    }
    timelineSnapshotBySession.value[sessionId] = value
  }

  function getTimelineSnapshot(sessionId: string | null | undefined) {
    if (!sessionId) return null
    return timelineSnapshotBySession.value[sessionId] ?? null
  }

  function setStoryMemorySnapshot(sessionId: string, value: StoryMemorySnapshotResponse | null | undefined) {
    if (!sessionId) return
    if (!value) {
      delete storyMemorySnapshotBySession.value[sessionId]
      return
    }
    storyMemorySnapshotBySession.value[sessionId] = value
  }

  function getStoryMemorySnapshot(sessionId: string | null | undefined) {
    if (!sessionId) return null
    return storyMemorySnapshotBySession.value[sessionId] ?? null
  }

  function resetDetailState() {
    detailTab.value = 'timeline'
    detailPage.value = 1
  }

  return {
    searchTerm,
    sessionSearchTerm,
    selectedSource,
    selectedLayer,
    selectedStatus,
    sessionViewMode,
    selectedSessionId,
    sessionListPage,
    sessionListPageSize,
    detailPage,
    detailPageSize,
    detailTab,
    listSnapshot,
    timelineSnapshotBySession,
    storyMemorySnapshotBySession,
    queryFilters,
    setSearchTerm,
    setSessionSearchTerm,
    setSelectedSource,
    setSelectedLayer,
    setSelectedStatus,
    setSessionViewMode,
    setSelectedSessionId,
    setSessionListPage,
    setSessionListPageSize,
    setDetailPage,
    setDetailPageSize,
    setDetailTab,
    setListSnapshot,
    setTimelineSnapshot,
    getTimelineSnapshot,
    setStoryMemorySnapshot,
    getStoryMemorySnapshot,
    resetDetailState,
  }
})
