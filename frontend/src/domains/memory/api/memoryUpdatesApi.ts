/**
 * 文件说明：前端业务域逻辑与接口封装。
 */

import api from '@/services/api'
import type {
  MemoryUpdateEvent,
  StoryMemoryPayload,
  SummaryMemorySnapshot,
} from '@/domains/story/api/storyGenerationApi'

export interface MemoryUpdateTimelineItem extends MemoryUpdateEvent {
  world_id?: string | null
}

export interface MemoryUpdateQueryFilters {
  session_id?: string
  world_id?: string
  source?: string
  memory_layer?: string
  status?: string
  search?: string
  date_from?: string
  date_to?: string
  page?: number
  page_size?: number
}

export interface MemoryUpdateQueryResponse {
  items: MemoryUpdateTimelineItem[]
  total: number
  page: number
  page_size: number
}

export interface MemorySummaryState {
  state: 'absent' | 'created' | 'reset' | 'recreated' | 'stale'
  current_summary?: SummaryMemorySnapshot | null
  last_semantic_event?: MemoryUpdateTimelineItem | null
}

export interface MemorySessionTimelineResponse {
  session_id: string
  world_id?: string | null
  items: MemoryUpdateTimelineItem[]
  total: number
  page: number
  page_size: number
  summary_state: MemorySummaryState
}

export interface StoryMemorySnapshotResponse {
  session_id: string
  story_id?: string | null
  world_id?: string | null
  timeline_total: number
  timeline_page: number
  timeline_page_size: number
  story_memory: StoryMemoryPayload
}

/** 处理 getMemoryUpdates 相关逻辑。 */
export async function getMemoryUpdates(filters: MemoryUpdateQueryFilters = {}): Promise<MemoryUpdateQueryResponse> {
  const response = await api.get<MemoryUpdateQueryResponse>('/memory-updates', { params: filters })
  return response.data
}

/** 处理 getSessionMemoryTimeline 相关逻辑。 */
export async function getSessionMemoryTimeline(
  sessionId: string,
  page = 1,
  pageSize = 100,
): Promise<MemorySessionTimelineResponse> {
  const response = await api.get<MemorySessionTimelineResponse>(
    `/story/session/${sessionId}/memory-updates`,
    { params: { page, page_size: pageSize } },
  )
  return response.data
}

/** 处理 getSessionStoryMemory 相关逻辑。 */
export async function getSessionStoryMemory(
  sessionId: string,
  page = 1,
  pageSize = 100,
  storyId?: string | null,
): Promise<StoryMemorySnapshotResponse> {
  const response = await api.get<StoryMemorySnapshotResponse>(
    `/story/session/${sessionId}/story-memory`,
    {
      params: {
        page,
        page_size: pageSize,
        story_id: storyId ?? undefined,
      },
    },
  )
  return response.data
}
