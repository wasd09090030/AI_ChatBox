/**
 * 文件说明：前端业务域逻辑与接口封装。
 */

import { computed, ref, type Ref } from 'vue'
import { useQueryClient } from '@tanstack/vue-query'
import { useToast } from '@/components/ui/toast'
import { lorebookManagementApi } from '@/domains/lorebook/api/lorebookManagementApi'
import { LOREBOOK_KEYS, useLorebookEntriesQuery } from '@/domains/lorebook/queries/useLorebookQueries'
import type { EntrySheetSubmitPayload, EntrySheetType } from '@/domains/lorebook/types'
import type { LorebookEntry } from '@/services/lorebookService'

/** 处理 useLorebookEntrySheet 相关逻辑。 */
export function useLorebookEntrySheet(selectedWorldId: Ref<string>) {
  const { toast } = useToast()
  const queryClient = useQueryClient()
  const { data: entriesData, isLoading: entriesLoading } = useLorebookEntriesQuery(selectedWorldId)

  const entrySheetOpen = ref(false)
  const entrySheetType = ref<EntrySheetType>('character')
  const editingEntry = ref<LorebookEntry | null>(null)
  const savingEntry = ref(false)

  const entries = computed(() => entriesData.value?.entries ?? [])

  function filteredByType(type: EntrySheetType) {
    return entries.value.filter((entry) => entry.type === type)
  }

  function openAddSheet(type: EntrySheetType) {
    entrySheetType.value = type
    editingEntry.value = null
    entrySheetOpen.value = true
  }

  function openEditSheet(entry: LorebookEntry) {
    entrySheetType.value = entry.type as EntrySheetType
    editingEntry.value = entry
    entrySheetOpen.value = true
  }

  function closeEntrySheet() {
    entrySheetOpen.value = false
  }

  async function submitEntry(payload: EntrySheetSubmitPayload) {
    if (!selectedWorldId.value) return
    savingEntry.value = true
    try {
      await lorebookManagementApi.saveEntry(selectedWorldId.value, payload)
      await queryClient.invalidateQueries({ queryKey: LOREBOOK_KEYS.entries(selectedWorldId.value) })
      entrySheetOpen.value = false
      toast({ title: payload.entryId ? '条目已更新' : '条目已添加' })
    } catch {
      toast({ title: '保存失败', variant: 'destructive' })
    } finally {
      savingEntry.value = false
    }
  }

  async function deleteEntry(entry: LorebookEntry) {
    if (!entry.id) return
    try {
      await lorebookManagementApi.deleteEntry(entry.id)
      await queryClient.invalidateQueries({ queryKey: LOREBOOK_KEYS.entries(selectedWorldId.value) })
      toast({ title: '条目已删除' })
    } catch {
      toast({ title: '删除失败', variant: 'destructive' })
    }
  }

  return {
    entries,
    entriesLoading,
    entrySheetOpen,
    entrySheetType,
    editingEntry,
    savingEntry,
    filteredByType,
    openAddSheet,
    openEditSheet,
    closeEntrySheet,
    submitEntry,
    deleteEntry,
  }
}