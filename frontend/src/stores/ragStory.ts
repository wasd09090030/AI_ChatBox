/**
 * RAG Story Store
 * 管理RAG故事生成的状态
 */

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { API_PREFIX } from '@/utils/constants'
import { useConfigStore } from '@/stores/config'
import { getUserId } from '@/domains/user/api/userIdentity'

/** 处理 asRecord 相关逻辑。 */
function asRecord(value: unknown): Record<string, unknown> {
  if (value && typeof value === 'object') {
    return value as Record<string, unknown>
  }
  return {}
}

/** 处理 asString 相关逻辑。 */
function asString(value: unknown, fallback = ''): string {
  if (typeof value === 'string') {
    return value
  }
  if (value === undefined || value === null) {
    return fallback
  }
  return String(value)
}

/** 处理 asStringArray 相关逻辑。 */
function asStringArray(value: unknown): string[] {
  if (!Array.isArray(value)) {
    return []
  }
  return value.map((item) => asString(item)).filter((item) => item.trim() !== '')
}

/** 处理 asRecordArray 相关逻辑。 */
function asRecordArray(value: unknown): Record<string, unknown>[] {
  if (!Array.isArray(value)) {
    return []
  }
  return value.map((item) => asRecord(item))
}

/** 处理 getErrorMessage 相关逻辑。 */
function getErrorMessage(error: unknown, fallback: string): string {
  if (error instanceof Error && error.message) {
    return error.message
  }

  const record = asRecord(error)
  if (typeof record.detail === 'string') {
    return record.detail
  }
  if (typeof record.message === 'string') {
    return record.message
  }

  return fallback
}

/** 处理 getValidationErrorMessage 相关逻辑。 */
function getValidationErrorMessage(detail: unknown, fallback: string): string {
  if (Array.isArray(detail)) {
    return detail
      .map((item) => {
        const detailRecord = asRecord(item)
        const loc = Array.isArray(detailRecord.loc)
          ? detailRecord.loc.map((part) => asString(part)).join('.')
          : ''
        const msg = asString(detailRecord.msg)
        return `${loc}: ${msg}`
      })
      .filter((item) => item !== ': ')
      .join(', ')
  }

  if (typeof detail === 'string') {
    return detail
  }

  return fallback
}

export interface World {
  id: string
  name: string
  description: string
  genre: string
  setting: string
  rules: string
  metadata: Record<string, unknown>
  created_at: string
  updated_at: string
}

export interface StorySegment {
  id: string
  prompt: string
  content: string
  retrievedContext: string[]
  retrievedHistory: string[]  // 历史对话引用
  timestamp: string
}

export interface Story {
  id: string
  worldId: string
  worldName: string
  title: string
  segments: StorySegment[]
  createdAt: string
  updatedAt: string
}

export interface StoryDebugSnapshot {
  activationLogs: Record<string, unknown>[]
  storyStateSnapshot: Record<string, unknown> | null
  summaryMemorySnapshot: Record<string, unknown> | null
  generationTime: number
  model: string
  contextsCount: number
  historyContextsCount: number
  updatedAt: string
}

// useRagStoryStore 状态仓库实例。
export const useRagStoryStore = defineStore('ragStory', () => {
  const configStore = useConfigStore()

  function getRequestHeaders(contentType = true): Record<string, string> {
    const headers: Record<string, string> = { 'X-User-ID': getUserId() }
    if (contentType) {
      headers['Content-Type'] = 'application/json'
    }
    return headers
  }

  // State
  const worlds = ref<World[]>([])
  const currentWorldId = ref<string | null>(null)
  const stories = ref<Story[]>([])
  const currentStoryId = ref<string | null>(null)
  const currentCharacterCardId = ref<string | null>(null)
  const currentPersonaId = ref<string | null>(null)
  const storyStateMode = ref<'off' | 'light' | 'strict'>('off')
  const latestDebugSnapshot = ref<StoryDebugSnapshot | null>(null)
  const isLoading = ref(false)
  const isGenerating = ref(false)
  const error = ref<string | null>(null)

  // API Base URL
  const API_BASE = API_PREFIX

  // Computed
  const currentWorld = computed(() => 
    worlds.value.find(w => w.id === currentWorldId.value)
  )

  const currentStory = computed(() => 
    stories.value.find(s => s.id === currentStoryId.value)
  )

  const worldStories = computed(() => 
    currentWorldId.value 
      ? stories.value.filter(s => s.worldId === currentWorldId.value)
      : []
  )

  // Actions
  async function loadWorlds() {
    isLoading.value = true
    error.value = null
    
    try {
      const response = await fetch(`${API_BASE}/worlds`)
      if (!response.ok) throw new Error('Failed to load worlds')
      
      const data = await response.json()
      worlds.value = data
    } catch (e: unknown) {
      error.value = getErrorMessage(e, 'Failed to load worlds')
      console.error('Error loading worlds:', e)
    } finally {
      isLoading.value = false
    }
  }

  async function createWorld(worldData: {
    name: string
    description: string
    genre: string
    setting: string
    rules: string
  }) {
    isLoading.value = true
    error.value = null
    
    try {
      const response = await fetch(`${API_BASE}/worlds`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(worldData)
      })
      
      if (!response.ok) throw new Error('Failed to create world')
      
      const newWorld = await response.json()
      worlds.value.push(newWorld)
      currentWorldId.value = newWorld.id
      
      return newWorld
    } catch (e: unknown) {
      error.value = getErrorMessage(e, 'Failed to create world')
      console.error('Error creating world:', e)
      throw e
    } finally {
      isLoading.value = false
    }
  }

  async function deleteWorld(worldId: string) {
    isLoading.value = true
    error.value = null
    
    try {
      const response = await fetch(`${API_BASE}/worlds/${worldId}`, {
        method: 'DELETE'
      })
      
      if (!response.ok) throw new Error('Failed to delete world')
      
      worlds.value = worlds.value.filter(w => w.id !== worldId)
      if (currentWorldId.value === worldId) {
        currentWorldId.value = null
      }
      
      // Also remove stories from this world
      stories.value = stories.value.filter(s => s.worldId !== worldId)
    } catch (e: unknown) {
      error.value = getErrorMessage(e, 'Failed to delete world')
      console.error('Error deleting world:', e)
      throw e
    } finally {
      isLoading.value = false
    }
  }

  async function updateWorld(worldId: string, worldData: Partial<Omit<World, 'id' | 'created_at' | 'updated_at'>>) {
    isLoading.value = true
    error.value = null
    
    try {
      const response = await fetch(`${API_BASE}/worlds/${worldId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(worldData)
      })
      
      if (!response.ok) throw new Error('Failed to update world')
      
      const updatedWorld = await response.json()
      
      // Update in local state
      const index = worlds.value.findIndex(w => w.id === worldId)
      if (index !== -1) {
        worlds.value[index] = updatedWorld
      }
      
      return updatedWorld
    } catch (e: unknown) {
      error.value = getErrorMessage(e, 'Failed to update world')
      console.error('Error updating world:', e)
      throw e
    } finally {
      isLoading.value = false
    }
  }

  function createNewStory(worldId: string, title: string = '未命名故事') {
    const world = worlds.value.find(w => w.id === worldId)
    if (!world) {
      error.value = 'World not found'
      return
    }

    // 使用API创建故事
    return createStoryOnServer(worldId, title)
  }

  async function createStoryOnServer(worldId: string, title: string) {
    isLoading.value = true
    error.value = null

    try {
      const response = await fetch(`${API_BASE}/stories`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          world_id: worldId,
          title: title,
          metadata: {}
        })
      })

      if (!response.ok) throw new Error('Failed to create story')

      const story = asRecord(await response.json())
      
      // 转换为前端格式
      const frontendStory: Story = {
        id: asString(story.id),
        worldId: asString(story.world_id),
        worldName: asString(story.world_name),
        title: asString(story.title),
        segments: [],
        createdAt: asString(story.created_at),
        updatedAt: asString(story.updated_at)
      }

      stories.value.push(frontendStory)
      currentStoryId.value = frontendStory.id

      return frontendStory
    } catch (e: unknown) {
      error.value = getErrorMessage(e, 'Failed to create story')
      console.error('Error creating story:', e)
      throw e
    } finally {
      isLoading.value = false
    }
  }

  async function updateStoryOnServer(storyId: string, updateData: { title?: string }) {
    try {
      const response = await fetch(`${API_BASE}/stories/${storyId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(updateData)
      })

      if (!response.ok) throw new Error('Failed to update story')

      return await response.json()
    } catch (e: unknown) {
      console.error('Error updating story:', e)
      throw e
    }
  }

  async function addSegmentToServer(
    storyId: string,
    prompt: string,
    content: string,
    retrievedContext: string[]
  ) {
    try {
      const response = await fetch(`${API_BASE}/stories/${storyId}/segments`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          prompt,
          content,
          retrieved_context: retrievedContext
        })
      })

      if (!response.ok) throw new Error('Failed to add segment')

      return await response.json()
    } catch (e: unknown) {
      console.error('Error adding segment:', e)
      throw e
    }
  }

  async function loadStoriesFromServer(worldId?: string) {
    isLoading.value = true
    error.value = null

    try {
      const url = worldId ? `${API_BASE}/stories?world_id=${worldId}` : `${API_BASE}/stories`
      const response = await fetch(url)

      if (!response.ok) throw new Error('Failed to load stories')

      const serverStories = await response.json()

      // 转换为前端格式,确保所有字段都存在
      stories.value = (Array.isArray(serverStories) ? serverStories : []).map((item) => {
        const storyRecord = asRecord(item)
        const segments = Array.isArray(storyRecord.segments) ? storyRecord.segments : []

        return {
          id: asString(storyRecord.id),
          worldId: asString(storyRecord.world_id),
          worldName: asString(storyRecord.world_name),
          title: asString(storyRecord.title),
          segments: segments.map((segmentItem) => {
            const segmentRecord = asRecord(segmentItem)
            return {
              id: asString(segmentRecord.id),
              prompt: asString(segmentRecord.prompt),
              content: asString(segmentRecord.content),
              retrievedContext: asStringArray(segmentRecord.retrieved_context ?? segmentRecord.retrievedContext),
              retrievedHistory: asStringArray(segmentRecord.retrieved_history ?? segmentRecord.retrievedHistory),
              timestamp: asString(segmentRecord.timestamp),
            }
          }),
          createdAt: asString(storyRecord.created_at),
          updatedAt: asString(storyRecord.updated_at),
        }
      })

      return stories.value
    } catch (e: unknown) {
      error.value = getErrorMessage(e, 'Failed to load stories')
      console.error('Error loading stories:', e)
      // 失败时尝试从localStorage加载
      loadStoriesFromLocal()
      return stories.value
    } finally {
      isLoading.value = false
    }
  }

  async function generateStory(prompt: string) {
    if (!currentStoryId.value || !currentWorldId.value) {
      error.value = 'No story or world selected'
      return
    }

    isGenerating.value = true
    error.value = null

    try {
      const response = await fetch(`${API_BASE}/story/generate`, {
        method: 'POST',
        headers: getRequestHeaders(true),
        body: JSON.stringify({
          session_id: currentStoryId.value,
          user_input: prompt,
          world_id: currentWorldId.value,
          provider: configStore.config.defaultProvider || undefined,
          base_url: configStore.providerBaseUrls[configStore.config.defaultProvider] || undefined,
          model: configStore.config.defaultModel || undefined,
          ...(currentCharacterCardId.value ? { character_card_id: currentCharacterCardId.value } : {}),
          ...(currentPersonaId.value ? { persona_id: currentPersonaId.value } : {}),
          ...(storyStateMode.value !== 'off' ? { story_state_mode: storyStateMode.value } : {}),
          max_tokens: configStore.config.maxTokens,
          temperature: configStore.config.temperature,
          use_rag: true,
          top_k: 5
        })
      })

      if (!response.ok) {
        const errorData = asRecord(await response.json())
        const errorMsg = getValidationErrorMessage(errorData.detail, 'Failed to generate story')
        throw new Error(errorMsg)
      }

      const data = asRecord(await response.json())
      const contextPayload = asRecordArray(data.contexts)
      const activationLogs = asRecordArray(data.activation_logs)
      const rawStoryStateSnapshot = data.story_state_snapshot
      const rawSummaryMemorySnapshot = data.summary_memory_snapshot

      latestDebugSnapshot.value = {
        activationLogs,
        storyStateSnapshot: rawStoryStateSnapshot ? asRecord(rawStoryStateSnapshot) : null,
        summaryMemorySnapshot: rawSummaryMemorySnapshot ? asRecord(rawSummaryMemorySnapshot) : null,
        generationTime: Number(data.generation_time ?? 0),
        model: asString(data.model),
        contextsCount: contextPayload.length,
        historyContextsCount: contextPayload.filter((ctx) => asString(ctx.type) === 'conversation_history').length,
        updatedAt: new Date().toISOString(),
      }

      // 添加片段到服务器
      const story = stories.value.find(s => s.id === currentStoryId.value)
      if (story) {
        // 从响应中提取内容
        const storyContent = asString(data.output_text)
        const contextEntries = contextPayload.map((ctx) => {
          const contextRecord = asRecord(ctx)
          return asString(contextRecord.name || ctx)
        })
        const historyEntries = contextPayload
          .map((ctx) => asRecord(ctx))
          .filter((ctx) => asString(ctx.type) === 'conversation_history')
          .map((ctx) => asString(ctx.name))
        
        // 保存到服务器
        await addSegmentToServer(currentStoryId.value, prompt, storyContent, contextEntries)
        
        // 更新本地状态
        const segment: StorySegment = {
          id: Date.now().toString(),
          prompt: prompt,
          content: storyContent,
          retrievedContext: contextEntries,
          retrievedHistory: historyEntries,
          timestamp: new Date().toISOString()
        }

        story.segments.push(segment)
        story.updatedAt = new Date().toISOString()
        
        // Update title if it's the first segment
        if (story.segments.length === 1 && story.title === '未命名故事') {
          const newTitle = prompt.slice(0, 30) + (prompt.length > 30 ? '...' : '')
          story.title = newTitle
          await updateStoryOnServer(story.id, { title: newTitle })
        }
      }

      return data
    } catch (e: unknown) {
      error.value = getErrorMessage(e, 'Failed to generate story')
      console.error('Error generating story:', e)
      throw e
    } finally {
      isGenerating.value = false
    }
  }

  /**
   * Generate story with streaming response
   * Returns an async generator for real-time updates
   */
  async function* generateStoryStream(prompt: string): AsyncGenerator<string> {
    const data = asRecord(await generateStory(prompt))
    const fullText = asString(data.output_text)
    if (fullText) {
      yield fullText
    }
  }

  function selectWorld(worldId: string) {
    currentWorldId.value = worldId
  }

  function selectStory(storyId: string) {
    currentStoryId.value = storyId
  }

  async function deleteStory(storyId: string) {
    try {
      const response = await fetch(`${API_BASE}/stories/${storyId}`, {
        method: 'DELETE'
      })

      if (response.ok) {
        stories.value = stories.value.filter(s => s.id !== storyId)
        if (currentStoryId.value === storyId) {
          currentStoryId.value = null
        }
      }
    } catch (e: unknown) {
      console.error('Error deleting story:', e)
      // 即使API失败也从本地删除
      stories.value = stories.value.filter(s => s.id !== storyId)
      if (currentStoryId.value === storyId) {
        currentStoryId.value = null
      }
    }
  }

  async function updateStoryTitle(storyId: string, newTitle: string) {
    const story = stories.value.find(s => s.id === storyId)
    if (story) {
      story.title = newTitle
      story.updatedAt = new Date().toISOString()
      
      // 更新到服务器
      try {
        await updateStoryOnServer(storyId, { title: newTitle })
      } catch (e) {
        console.error('Error updating title on server:', e)
      }
    }
  }

  function loadStoriesFromLocal() {
    try {
      const saved = localStorage.getItem('rag-stories')
      if (saved) {
        const parsed = JSON.parse(saved)
        // 确保每个 segment 都有 retrievedContext 和 retrievedHistory 字段
        stories.value = parsed.map((story: Story) => ({
          ...story,
          segments: (story.segments || []).map(seg => ({
            ...seg,
            retrievedContext: seg.retrievedContext || [],
            retrievedHistory: seg.retrievedHistory || []
          }))
        }))
      }
    } catch (e) {
      console.error('Error loading stories from localStorage:', e)
    }
  }

  function clearError() {
    error.value = null
  }

  function setRoleplayBindings(payload: {
    characterCardId?: string | null
    personaId?: string | null
    stateMode?: 'off' | 'light' | 'strict'
  }) {
    if (payload.characterCardId !== undefined) {
      currentCharacterCardId.value = payload.characterCardId
    }
    if (payload.personaId !== undefined) {
      currentPersonaId.value = payload.personaId
    }
    if (payload.stateMode !== undefined) {
      storyStateMode.value = payload.stateMode
    }
  }

  function clearRoleplayBindings() {
    currentCharacterCardId.value = null
    currentPersonaId.value = null
    storyStateMode.value = 'off'
  }

  return {
    // State
    worlds,
    currentWorldId,
    stories,
    currentStoryId,
    currentCharacterCardId,
    currentPersonaId,
    storyStateMode,
    latestDebugSnapshot,
    isLoading,
    isGenerating,
    error,
    
    // Computed
    currentWorld,
    currentStory,
    worldStories,
    
    // Actions
    loadWorlds,
    createWorld,
    updateWorld,
    deleteWorld,
    createNewStory,
    generateStory,
    generateStoryStream,
    selectWorld,
    selectStory,
    deleteStory,
    updateStoryTitle,
    loadStoriesFromLocal,
    loadStoriesFromServer,
    setRoleplayBindings,
    clearRoleplayBindings,
    clearError
  }
})
