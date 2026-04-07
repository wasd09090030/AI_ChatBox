/**
 * Storage Service — Cross-Device Sync Edition
 *
 * Read strategy  (WRITE-THROUGH CACHE — no console 404 noise):
 *   1. Return localStorage immediately (fast, offline-safe, no network request)
 *   2. Explicit `pullFromRemote(key)` to overwrite local cache from backend
 *      — called by stores only when localStorage is empty (new device scenario)
 *
 * Write strategy:
 *   1. Write localStorage synchronously
 *   2. Fire-and-forget PUT to backend (best-effort, errors swallowed)
 *
 * API keys excluded from remote sync (see NO_REMOTE_SYNC).
 */

import { API_BASE_URL } from '@/utils/constants'

// Keys that stay local-only (relative key, without the 'chatbox_' prefix)
const NO_REMOTE_SYNC = new Set(['api_keys_v2', 'api_keys'])

const REMOTE_BASE = API_BASE_URL
  ? `${API_BASE_URL}/api/client-storage`
  : '/api/client-storage'

class StorageService {
  private prefix = 'chatbox_'

  private fullKey(key: string): string {
    return this.prefix + key
  }

  private isRemoteSyncable(key: string): boolean {
    return !NO_REMOTE_SYNC.has(key)
  }

  // ── READ — localStorage first, no network request ──────────────────────
  async getStorage(key: string): Promise<string | null> {
    const localKey = this.fullKey(key)
    const value = localStorage.getItem(localKey)
    if (import.meta.env.DEV) {
      console.log(`[Storage] GET ${localKey} ← localStorage (${value ? value.length + 'b' : 'null'})`)
    }
    return value
  }

  /**
   * Explicit pull from backend — only called when localStorage is empty
   * (i.e., fresh device that has never seen this data).
   * Returns the backend value and also writes it to localStorage.
   */
  async pullFromRemote(key: string): Promise<string | null> {
    if (!this.isRemoteSyncable(key)) return null
    const localKey = this.fullKey(key)
    try {
      const res = await fetch(`${REMOTE_BASE}/${encodeURIComponent(localKey)}`)
      if (res.ok) {
        const data = await res.json()
        localStorage.setItem(localKey, data.value)
        if (import.meta.env.DEV) {
          console.log(`[Storage] PULL ${localKey} ← backend (${data.value.length}b)`)
        }
        return data.value
      }
      // 404 = key not on backend yet — caller handles null
    } catch {
      // Network unavailable — caller handles null
    }
    return null
  }

  // ── WRITE — localStorage + background push ────────────────────────────
  async setStorage(key: string, value: string): Promise<boolean> {
    const localKey = this.fullKey(key)

    try {
      localStorage.setItem(localKey, value)
    } catch (err) {
      console.error('[Storage] localStorage write failed:', err)
      return false
    }

    if (this.isRemoteSyncable(key)) {
      fetch(`${REMOTE_BASE}/${encodeURIComponent(localKey)}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ value }),
      }).catch(() => { /* backend optional */ })
    }

    if (import.meta.env.DEV) {
      console.log(`[Storage] SET ${localKey} (${value.length}b)`)
    }
    return true
  }

  // ── DELETE ─────────────────────────────────────────────────────────────
  async deleteStorage(key: string): Promise<boolean> {
    const localKey = this.fullKey(key)
    localStorage.removeItem(localKey)

    if (this.isRemoteSyncable(key)) {
      fetch(`${REMOTE_BASE}/${encodeURIComponent(localKey)}`, { method: 'DELETE' })
        .catch(() => {})
    }

    if (import.meta.env.DEV) {
      console.log(`[Storage] DELETE ${localKey}`)
    }
    return true
  }

  // ── CLEAR ALL ──────────────────────────────────────────────────────────
  async clearAll(): Promise<boolean> {
    const keys = Object.keys(localStorage).filter((k) => k.startsWith(this.prefix))
    keys.forEach((k) => localStorage.removeItem(k))
    fetch(`${REMOTE_BASE}`, { method: 'DELETE' }).catch(() => {})
    console.log(`[Storage] Cleared ${keys.length} local items + queued remote clear`)
    return true
  }

  // ── HELPERS ────────────────────────────────────────────────────────────
  getAllKeys(): string[] {
    try {
      return Object.keys(localStorage)
        .filter((key) => key.startsWith(this.prefix))
        .map((key) => key.substring(this.prefix.length))
    } catch {
      return []
    }
  }

  hasKey(key: string): boolean {
    try {
      return localStorage.getItem(this.fullKey(key)) !== null
    } catch {
      return false
    }
  }

  getStorageSize(): number {
    try {
      let total = 0
      Object.keys(localStorage)
        .filter((key) => key.startsWith(this.prefix))
        .forEach((key) => {
          const v = localStorage.getItem(key)
          if (v) total += key.length + v.length
        })
      return total
    } catch {
      return 0
    }
  }
}

// Export singleton instance
export const storage = new StorageService()

// For debugging in development
if (import.meta.env.DEV) {
  ;(window as Window & { storage?: StorageService }).storage = storage
}
