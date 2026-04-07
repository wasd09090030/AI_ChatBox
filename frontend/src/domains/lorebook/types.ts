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