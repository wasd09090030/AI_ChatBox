import { defineStore } from 'pinia'
import { ref, watch } from 'vue'
import { toast } from '@/components/ui/toast'
import { buildStorySessionId, createSessionV2 } from '@/domains/story/api/storyGenerationApi'
import { storyLibraryApi } from '@/domains/story/api/storyLibraryApi'
import { useStoryDraftStateStore } from '@/stores/storyDraftState'
import type { StoredStory } from '@/components/story/types'

export const useStoryWorkspaceStore = defineStore('storyWorkspace', () => {
  const storyDraftStore = useStoryDraftStateStore()
  const selectedWorldId = ref('')
  const stories = ref<StoredStory[]>([])
  const storiesLoading = ref(false)
  const currentStory = ref<StoredStory | null>(null)
  const v2SessionId = ref('')

  const showNewStory = ref(false)
  const newStoryTitle = ref('')
  const creatingStory = ref(false)

  watch(selectedWorldId, async (worldId, previousWorldId) => {
    if (worldId === previousWorldId) return
    v2SessionId.value = ''
    currentStory.value = null

    if (!worldId) {
      stories.value = []
      return
    }

    await loadStories(worldId)
  })

  async function loadStories(worldId: string) {
    storiesLoading.value = true
    const previousCurrentStoryId = currentStory.value?.id ?? null
    try {
      const list = await storyLibraryApi.listByWorld(worldId)
      stories.value = list
      currentStory.value = previousCurrentStoryId
        ? list.find((item) => item.id === previousCurrentStoryId) ?? null
        : null
    } catch {
      toast({ title: '加载失败', description: '无法获取故事列表', variant: 'destructive' })
      stories.value = []
      currentStory.value = null
    } finally {
      storiesLoading.value = false
    }
  }

  async function ensureV2Session(storyId: string) {
    const sessionId = buildStorySessionId(storyId)
    if (v2SessionId.value === sessionId) return sessionId
    try {
      await createSessionV2(sessionId, selectedWorldId.value || undefined)
    } catch {
      // Session may already exist. The stable local session id remains valid.
    }
    v2SessionId.value = sessionId
    return sessionId
  }

  async function createStory() {
    if (!selectedWorldId.value || !newStoryTitle.value.trim()) return

    creatingStory.value = true
    try {
      const createdStory = await storyLibraryApi.create({
        world_id: selectedWorldId.value,
        title: newStoryTitle.value.trim(),
      })
      stories.value.unshift(createdStory)
      currentStory.value = createdStory
      v2SessionId.value = ''
      showNewStory.value = false
      newStoryTitle.value = ''
      toast({ title: '故事已创建', description: `"${createdStory.title}" 已就绪` })
    } catch {
      toast({ title: '创建失败', variant: 'destructive' })
    } finally {
      creatingStory.value = false
    }
  }

  async function deleteStory(story: StoredStory) {
    try {
      await storyLibraryApi.remove(story.id)
      stories.value = stories.value.filter((item) => item.id !== story.id)
      storyDraftStore.deleteStoryDraft(story.id)
      if (currentStory.value?.id === story.id) {
        currentStory.value = null
        v2SessionId.value = ''
      }
      toast({ title: '已删除', description: `"${story.title}" 已删除` })
    } catch {
      toast({ title: '删除失败', variant: 'destructive' })
    }
  }

  function selectStory(story: StoredStory) {
    const matchedStory = stories.value.find((item) => item.id === story.id) ?? story
    currentStory.value = matchedStory
    v2SessionId.value = ''
  }

  function syncStory(updatedStory: StoredStory) {
    const index = stories.value.findIndex((item) => item.id === updatedStory.id)
    if (index >= 0) {
      stories.value[index] = updatedStory
    } else {
      stories.value.unshift(updatedStory)
    }
    if (currentStory.value?.id === updatedStory.id) {
      currentStory.value = updatedStory
    }
  }

  return {
    selectedWorldId,
    stories,
    storiesLoading,
    currentStory,
    v2SessionId,
    showNewStory,
    newStoryTitle,
    creatingStory,
    loadStories,
    ensureV2Session,
    createStory,
    deleteStory,
    selectStory,
    syncStory,
  }
})
