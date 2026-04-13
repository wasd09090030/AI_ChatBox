/**
 * 文件说明：前端状态管理与会话数据维护。
 */

import { defineStore } from 'pinia'
import { ref } from 'vue'
import type { StoryMode } from '@/components/story/types'

export type StoryPageMode = 'improv' | 'scripted'
export type StoryProgressIntent = 'hold' | 'advance' | 'complete'
export type StoryDialogueMode = 'auto' | 'focused' | 'required'

export interface SharedStoryDraftState {
  selectedPersonaId: string | null
  selectedPrincipalCharacterId: string | null
  dialogueMode: StoryDialogueMode
  dialogueTarget: string
  dialogueIntent: string
  dialogueStyleHint: string
  selectedContextEntryIds: string[]
  selectedFocusTemplateId: string
}

export interface RouteStoryDraftState {
  userInput: string
  storyMode: StoryMode
  authorsNote: string
  instruction: string
  progressIntent: StoryProgressIntent
}

/** 处理 createSharedStoryDraft 相关逻辑。 */
function createSharedStoryDraft(): SharedStoryDraftState {
  return {
    selectedPersonaId: null,
    selectedPrincipalCharacterId: null,
    dialogueMode: 'auto',
    dialogueTarget: '',
    dialogueIntent: '',
    dialogueStyleHint: '',
    selectedContextEntryIds: [],
    selectedFocusTemplateId: '',
  }
}

/** 处理 createRouteStoryDraft 相关逻辑。 */
function createRouteStoryDraft(pageMode: StoryPageMode): RouteStoryDraftState {
  return {
    userInput: '',
    storyMode: pageMode === 'scripted' ? 'narrative' : 'choices',
    authorsNote: '',
    instruction: '',
    progressIntent: 'hold',
  }
}

// useStoryDraftStateStore 状态仓库实例。
export const useStoryDraftStateStore = defineStore('storyDraftState', () => {
  const sharedDrafts = ref<Record<string, SharedStoryDraftState>>({})
  const routeDrafts = ref<Record<string, RouteStoryDraftState>>({})

  function ensureSharedDraft(storyId: string) {
    if (!sharedDrafts.value[storyId]) {
      sharedDrafts.value[storyId] = createSharedStoryDraft()
    }
    return sharedDrafts.value[storyId]
  }

  function ensureRouteDraft(storyId: string, pageMode: StoryPageMode) {
    const routeKey = `${storyId}:${pageMode}`
    if (!routeDrafts.value[routeKey]) {
      routeDrafts.value[routeKey] = createRouteStoryDraft(pageMode)
    }
    return routeDrafts.value[routeKey]
  }

  function deleteStoryDraft(storyId: string) {
    delete sharedDrafts.value[storyId]
    delete routeDrafts.value[`${storyId}:improv`]
    delete routeDrafts.value[`${storyId}:scripted`]
  }

  return {
    ensureSharedDraft,
    ensureRouteDraft,
    deleteStoryDraft,
  }
})
