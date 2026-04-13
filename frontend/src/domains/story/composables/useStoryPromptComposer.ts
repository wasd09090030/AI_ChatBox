/**
 * 文件说明：前端业务域逻辑与接口封装。
 */

import { computed, ref, type ComputedRef, type Ref } from 'vue'
import type { LorebookEntry } from '@/services/lorebookService'
import type { PromptFocusTemplate } from '@/config/prompts'

export type ComposerTab = 'character' | 'location' | 'event'

interface UseStoryPromptComposerArgs {
  lorebookEntries: ComputedRef<LorebookEntry[]>
  promptFocusTemplates: PromptFocusTemplate[]
  selectedContextEntryIds?: Ref<string[]>
  selectedFocusTemplateId?: Ref<string>
}

/** 处理 useStoryPromptComposer 相关逻辑。 */
export function useStoryPromptComposer(args: UseStoryPromptComposerArgs) {
  const showPromptComposer = ref(false)
  const selectedContextEntryIds = args.selectedContextEntryIds ?? ref<string[]>([])
  const selectedFocusTemplateId = args.selectedFocusTemplateId ?? ref('')
  const draftContextEntryIds = ref<string[]>([])
  const draftFocusTemplateId = ref('')
  const currentComposerTab = ref<ComposerTab>('character')
  const composerSearchQuery = ref('')
  const composerPreviewEntryId = ref('')

  const characterEntries = computed(() => args.lorebookEntries.value.filter((entry) => entry.type === 'character'))
  const locationEntries = computed(() => args.lorebookEntries.value.filter((entry) => entry.type === 'location'))
  const eventEntries = computed(() => args.lorebookEntries.value.filter((entry) => entry.type === 'event'))

  function filterComposerEntries(entries: LorebookEntry[]) {
    const query = composerSearchQuery.value.trim().toLowerCase()
    if (!query) return entries
    return entries.filter((entry) => `${entry.name} ${entry.description}`.toLowerCase().includes(query))
  }

  const filteredCharacterEntries = computed(() => filterComposerEntries(characterEntries.value))
  const filteredLocationEntries = computed(() => filterComposerEntries(locationEntries.value))
  const filteredEventEntries = computed(() => filterComposerEntries(eventEntries.value))

  const currentComposerEntries = computed(() => {
    if (currentComposerTab.value === 'character') return filteredCharacterEntries.value
    if (currentComposerTab.value === 'location') return filteredLocationEntries.value
    return filteredEventEntries.value
  })

  const composerPreviewEntry = computed(() => {
    return currentComposerEntries.value.find((entry) => entry.id === composerPreviewEntryId.value)
      ?? currentComposerEntries.value[0]
      ?? null
  })

  const selectedContextEntries = computed(() => {
    const selectedIds = new Set(selectedContextEntryIds.value)
    return args.lorebookEntries.value.filter((entry) => entry.id && selectedIds.has(entry.id))
  })

  const activeFocusTemplate = computed(() => (
    args.promptFocusTemplates.find((item) => item.id === selectedFocusTemplateId.value) ?? null
  ))

  const promptDrawerBadgeText = computed(() => {
    const countText = `${selectedContextEntries.value.length}设定`
    return activeFocusTemplate.value ? `${countText} + 重点` : `${countText} + 无重点`
  })

  function resetComposerState() {
    showPromptComposer.value = false
    draftContextEntryIds.value = []
    draftFocusTemplateId.value = ''
    currentComposerTab.value = 'character'
    composerSearchQuery.value = ''
    composerPreviewEntryId.value = ''
  }

  function openPromptComposer() {
    draftContextEntryIds.value = [...selectedContextEntryIds.value]
    draftFocusTemplateId.value = selectedFocusTemplateId.value
    composerSearchQuery.value = ''
    composerPreviewEntryId.value = ''
    currentComposerTab.value = 'character'
    showPromptComposer.value = true
  }

  function openComposerEntry(entry: LorebookEntry) {
    composerPreviewEntryId.value = entry.id || ''
  }

  function toggleDraftContextEntry(entry: LorebookEntry) {
    if (!entry.id) return
    const next = new Set(draftContextEntryIds.value)
    if (next.has(entry.id)) next.delete(entry.id)
    else next.add(entry.id)
    draftContextEntryIds.value = [...next]
  }

  function isDraftEntrySelected(entry: LorebookEntry) {
    return !!entry.id && draftContextEntryIds.value.includes(entry.id)
  }

  function applyPromptComposerSelection() {
    selectedContextEntryIds.value = [...new Set(draftContextEntryIds.value)]
    selectedFocusTemplateId.value = draftFocusTemplateId.value
    showPromptComposer.value = false
  }

  function clearPromptComposerSelection() {
    selectedContextEntryIds.value = []
    selectedFocusTemplateId.value = ''
    draftContextEntryIds.value = []
    draftFocusTemplateId.value = ''
  }

  function removeSelectedContextEntry(entryId: string | null) {
    if (!entryId) return
    selectedContextEntryIds.value = selectedContextEntryIds.value.filter((id) => id !== entryId)
    draftContextEntryIds.value = draftContextEntryIds.value.filter((id) => id !== entryId)
  }

  function clearSelectedFocusTemplate() {
    selectedFocusTemplateId.value = ''
    draftFocusTemplateId.value = ''
  }

  return {
    showPromptComposer,
    selectedContextEntryIds,
    selectedFocusTemplateId,
    draftContextEntryIds,
    draftFocusTemplateId,
    currentComposerTab,
    composerSearchQuery,
    composerPreviewEntryId,
    characterEntries,
    locationEntries,
    eventEntries,
    filteredCharacterEntries,
    filteredLocationEntries,
    filteredEventEntries,
    currentComposerEntries,
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
  }
}
