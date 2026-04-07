import { storeToRefs } from 'pinia'
import { useWorldsQuery } from '@/domains/lorebook/queries/useLorebookQueries'
import { useStoryWorkspaceStore } from '@/stores/storyWorkspace'
import type { StoredStory } from '@/components/story/types'

interface UseStoryLibraryOptions {
  onStoryChanged?: (story: StoredStory | null) => void
}

export function useStoryLibrary(options: UseStoryLibraryOptions = {}) {
  const storyWorkspace = useStoryWorkspaceStore()
  const { data: worlds, isLoading: worldsLoading } = useWorldsQuery()
  const {
    selectedWorldId,
    stories,
    storiesLoading,
    currentStory,
    v2SessionId,
    showNewStory,
    newStoryTitle,
    creatingStory,
  } = storeToRefs(storyWorkspace)

  function selectStory(story: StoredStory) {
    storyWorkspace.selectStory(story)
    options.onStoryChanged?.(currentStory.value)
  }

  async function createStory() {
    await storyWorkspace.createStory()
    options.onStoryChanged?.(currentStory.value)
  }

  async function deleteStory(story: StoredStory) {
    await storyWorkspace.deleteStory(story)
    options.onStoryChanged?.(currentStory.value)
  }

  return {
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
    loadStories: storyWorkspace.loadStories,
    ensureV2Session: storyWorkspace.ensureV2Session,
    createStory,
    deleteStory,
    selectStory,
    syncStory: storyWorkspace.syncStory,
  }
}
