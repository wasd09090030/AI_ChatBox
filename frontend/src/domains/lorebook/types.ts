/**
 * 文件说明：前端业务域逻辑与接口封装。
 */

import type {
  BulkImportEntry,
  CharacterEntryCreate,
  EventEntryCreate,
  LocationEntryCreate,
} from '@/services/lorebookService'

export type EntrySheetType = 'character' | 'location' | 'event'
export type EntrySheetFormData = CharacterEntryCreate | LocationEntryCreate | EventEntryCreate

export interface EntrySheetSubmitPayload {
  entryId: string | null
  type: EntrySheetType
  data: EntrySheetFormData
}

export interface BulkImportResult {
  imported: number
  failed: number
  details: {
    success: string[]
    failed: Array<{ name: string; reason: string }>
  }
}

export type ParsedBulkImportEntries = BulkImportEntry[]