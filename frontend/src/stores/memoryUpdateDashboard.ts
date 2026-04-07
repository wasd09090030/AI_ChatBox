import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import type {
  MemorySessionTimelineResponse,
  MemoryUpdateQueryFilters,
  MemoryUpdateQueryResponse,
} from '@/domains/memory/api/memoryUpdatesApi'

export type MemoryUpdateDetailTab = 'timeline' | 'semantic' | 'entity'
export type MemoryUpdateTimeRange = 'all' | '1h' | '24h' | '7d'

function buildDateRange(range: MemoryUpdateTimeRange) {
  if (range === 'all') return { date_from: undefined, date_to: undefined }
  const now = new Date()
  const start = new Date(now)
  if (range === '1h') start.setHours(start.getHours() - 1)
  if (range === '24h') start.setHours(start.getHours() - 24)
  if (range === '7d') start.setDate(start.getDate() - 7)
  return {
    date_from: start.toISOString(),
    date_to: now.toISOString(),
  }
}

export const useMemoryUpdateDashboardStore = defineStore('memoryUpdateDashboard', () => {
  const searchTerm = ref('')
  const selectedSource = ref('all')
  const selectedLayer = ref('all')
  const selectedStatus = ref('all')
  const selectedTimeRange = ref<MemoryUpdateTimeRange>('24h')
  const selectedSessionId = ref<string | null>(null)
  const detailPage = ref(1)
  const detailPageSize = ref(100)
  const detailTab = ref<MemoryUpdateDetailTab>('timeline')

  const listSnapshot = ref<MemoryUpdateQueryResponse | null>(null)
  const timelineSnapshotBySession = ref<Record<string, MemorySessionTimelineResponse>>({})

  const queryFilters = computed<MemoryUpdateQueryFilters>(() => {
    const range = buildDateRange(selectedTimeRange.value)
    return {
      search: searchTerm.value.trim() || undefined,
      source: selectedSource.value === 'all' ? undefined : selectedSource.value,
      memory_layer: selectedLayer.value === 'all' ? undefined : selectedLayer.value,
      status: selectedStatus.value === 'all' ? undefined : selectedStatus.value,
      date_from: range.date_from,
      date_to: range.date_to,
      page: 1,
      page_size: 120,
    }
  })

  function setSearchTerm(value: string) {
    searchTerm.value = value
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

  function setSelectedTimeRange(value: MemoryUpdateTimeRange) {
    selectedTimeRange.value = value
  }

  function setSelectedSessionId(value: string | null) {
    selectedSessionId.value = value
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

  function resetDetailState() {
    detailTab.value = 'timeline'
    detailPage.value = 1
  }

  return {
    searchTerm,
    selectedSource,
    selectedLayer,
    selectedStatus,
    selectedTimeRange,
    selectedSessionId,
    detailPage,
    detailPageSize,
    detailTab,
    listSnapshot,
    timelineSnapshotBySession,
    queryFilters,
    setSearchTerm,
    setSelectedSource,
    setSelectedLayer,
    setSelectedStatus,
    setSelectedTimeRange,
    setSelectedSessionId,
    setDetailPage,
    setDetailPageSize,
    setDetailTab,
    setListSnapshot,
    setTimelineSnapshot,
    getTimelineSnapshot,
    resetDetailState,
  }
})
