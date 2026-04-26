import { computed, ref } from 'vue'
import { defineStore } from 'pinia'
import {
  claimLegacyIdentity,
  fetchCurrentUser,
  login as loginApi,
  logout as logoutApi,
  register as registerApi,
  type AuthenticatedUser,
  type LegacyClaimResponse,
} from '@/domains/auth/api/authApi'
import { isAppError, normalizeApiError } from '@/services/errors'
import { storage } from '@/utils/storage'
import { getLegacyUserId } from '@/domains/user/api/userIdentity'

type AuthMode = 'login' | 'register'

let restorePromise: Promise<AuthenticatedUser | null> | null = null

export const useAuthStore = defineStore('auth', () => {
  const user = ref<AuthenticatedUser | null>(null)
  const isResolved = ref(false)
  const isBusy = ref(false)
  const lastError = ref<string | null>(null)
  const lastAuthMode = ref<AuthMode>('login')
  const legacyClaimResult = ref<LegacyClaimResponse | null>(null)

  const isAuthenticated = computed(() => user.value !== null)
  const legacyUserId = computed(() => getLegacyUserId())

  function applyAuthenticatedUser(nextUser: AuthenticatedUser | null) {
    user.value = nextUser
    storage.setUserScope(nextUser?.user_id ?? null)
    isResolved.value = true
    return nextUser
  }

  async function ensureResolved(force = false): Promise<AuthenticatedUser | null> {
    if (isResolved.value && !force) {
      return user.value
    }
    if (restorePromise) {
      return restorePromise
    }

    restorePromise = (async () => {
      isBusy.value = true
      lastError.value = null
      try {
        const currentUser = await fetchCurrentUser()
        return applyAuthenticatedUser(currentUser)
      } catch (error) {
        const normalized = normalizeApiError(error)
        if (normalized.status && normalized.status !== 401) {
          lastError.value = normalized.message
        }
        return applyAuthenticatedUser(null)
      } finally {
        isBusy.value = false
        restorePromise = null
      }
    })()

    return restorePromise
  }

  async function login(payload: { login_identifier: string; password: string }) {
    isBusy.value = true
    lastError.value = null
    lastAuthMode.value = 'login'
    try {
      const authenticatedUser = await loginApi(payload)
      return applyAuthenticatedUser(authenticatedUser)
    } catch (error) {
      const normalized = normalizeApiError(error)
      lastError.value = normalized.message
      throw normalized
    } finally {
      isBusy.value = false
    }
  }

  async function register(payload: {
    login_identifier: string
    password: string
    display_name?: string
  }) {
    isBusy.value = true
    lastError.value = null
    lastAuthMode.value = 'register'
    try {
      const authenticatedUser = await registerApi(payload)
      return applyAuthenticatedUser(authenticatedUser)
    } catch (error) {
      const normalized = normalizeApiError(error)
      lastError.value = normalized.message
      throw normalized
    } finally {
      isBusy.value = false
    }
  }

  async function logout() {
    isBusy.value = true
    lastError.value = null
    try {
      await logoutApi()
    } catch (error) {
      const normalized = normalizeApiError(error)
      if (!isAppError(normalized) || normalized.status !== 401) {
        lastError.value = normalized.message
      }
    } finally {
      applyAuthenticatedUser(null)
      legacyClaimResult.value = null
      isBusy.value = false
    }
  }

  async function claimLegacyData() {
    const legacyId = legacyUserId.value
    if (!legacyId || !user.value) {
      legacyClaimResult.value = null
      return null
    }
    try {
      const result = await claimLegacyIdentity({ legacy_user_id: legacyId })
      legacyClaimResult.value = result
      return result
    } catch (error) {
      const normalized = normalizeApiError(error)
      lastError.value = normalized.message
      throw normalized
    }
  }

  function clearError() {
    lastError.value = null
  }

  return {
    user,
    isResolved,
    isBusy,
    lastError,
    lastAuthMode,
    legacyUserId,
    legacyClaimResult,
    isAuthenticated,
    ensureResolved,
    login,
    register,
    logout,
    claimLegacyData,
    clearError,
  }
})
