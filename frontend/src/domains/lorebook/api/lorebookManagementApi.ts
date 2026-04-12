/**
 * 文件说明：前端业务域逻辑与接口封装。
 */

import {
  lorebookApi,
  worldApi,
  type BulkImportEntry,
  type CharacterEntryCreate,
  type EventEntryCreate,
  type LocationEntryCreate,
  type WorldCreate,
} from '@/services/lorebookService'
import type { EntrySheetSubmitPayload } from '@/domains/lorebook/types'

/** 功能：函数 buildEntryUpdatePayload，负责 buildEntryUpdatePayload 相关处理。 */
function buildEntryUpdatePayload(worldId: string, payload: EntrySheetSubmitPayload) {
  return {
    entry_type: payload.type,
    world_id: worldId,
    data: payload.data as CharacterEntryCreate | LocationEntryCreate | EventEntryCreate,
  }
}

// 变量作用：变量 lorebookManagementApi，用于 lorebookManagementApi 相关配置或状态。
export const lorebookManagementApi = {
  createWorld(payload: WorldCreate) {
    return worldApi.create(payload)
  },

  updateWorld(worldId: string, payload: WorldCreate) {
    return worldApi.update(worldId, payload)
  },

  deleteWorld(worldId: string) {
    return worldApi.delete(worldId)
  },

  saveEntry(worldId: string, payload: EntrySheetSubmitPayload) {
    if (payload.entryId) {
      return lorebookApi.updateEntry(payload.entryId, buildEntryUpdatePayload(worldId, payload))
    }

    if (payload.type === 'character') {
      return lorebookApi.addCharacter(worldId, payload.data as CharacterEntryCreate)
    }
    if (payload.type === 'location') {
      return lorebookApi.addLocation(worldId, payload.data as LocationEntryCreate)
    }
    return lorebookApi.addEvent(worldId, payload.data as EventEntryCreate)
  },

  deleteEntry(entryId: string) {
    return lorebookApi.deleteEntry(entryId)
  },

  bulkImport(worldId: string, entries: BulkImportEntry[]) {
    return lorebookApi.bulkImport(worldId, entries)
  },
}