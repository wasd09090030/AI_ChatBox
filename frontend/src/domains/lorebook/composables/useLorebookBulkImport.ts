/**
 * 文件说明：前端业务域逻辑与接口封装。
 */

import { ref, type Ref } from 'vue'
import { useQueryClient } from '@tanstack/vue-query'
import { useToast } from '@/components/ui/toast'
import { lorebookManagementApi } from '@/domains/lorebook/api/lorebookManagementApi'
import { LOREBOOK_KEYS } from '@/domains/lorebook/queries/useLorebookQueries'
import type { BulkImportEntry } from '@/services/lorebookService'
import type { BulkImportResult } from '@/domains/lorebook/types'

/** 功能：函数 useLorebookBulkImport，负责 useLorebookBulkImport 相关处理。 */
export function useLorebookBulkImport(selectedWorldId: Ref<string>) {
  const { toast } = useToast()
  const queryClient = useQueryClient()

  const bulkImportOpen = ref(false)
  const importing = ref(false)
  const importResult = ref<BulkImportResult | null>(null)

  function openBulkImport() {
    importResult.value = null
    bulkImportOpen.value = true
  }

  function closeBulkImport() {
    importResult.value = null
    bulkImportOpen.value = false
  }

  async function importEntries(entries: BulkImportEntry[]) {
    if (!selectedWorldId.value) return
    importing.value = true
    importResult.value = null
    try {
      const result = await lorebookManagementApi.bulkImport(selectedWorldId.value, entries)
      importResult.value = result as BulkImportResult
      await queryClient.invalidateQueries({ queryKey: LOREBOOK_KEYS.entries(selectedWorldId.value) })
      toast({
        title: `批量导入完成：成功 ${result.imported} 条，失败 ${result.failed} 条`,
        variant: result.failed > 0 ? 'destructive' : 'default',
      })
    } catch {
      toast({ title: '导入失败', variant: 'destructive' })
    } finally {
      importing.value = false
    }
  }

  return {
    bulkImportOpen,
    importing,
    importResult,
    openBulkImport,
    closeBulkImport,
    importEntries,
  }
}