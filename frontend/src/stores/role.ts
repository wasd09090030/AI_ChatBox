/**
 * Role Store
 *
 * Manages AI assistant roles
 */

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { Role } from '@/utils/types'
import { DEFAULT_ROLES } from '@/utils/constants'
import {
  fetchRoleState,
  usePersistRolesMutation,
  usePersistCurrentRoleIdMutation,
} from '@/domains/role/queries/useRolePersistence'

// 变量作用：变量 useRoleStore，用于 useRoleStore 相关配置或状态。
export const useRoleStore = defineStore('role', () => {
  // State
  const roles = ref<Role[]>([])
  const currentRoleId = ref<string>('default')
  const isLoading = ref(false)
  const error = ref<string | null>(null)

  const persistRolesMutation = usePersistRolesMutation()
  const persistCurrentRoleIdMutation = usePersistCurrentRoleIdMutation()

  function getErrorMessage(error: unknown, fallback: string) {
    if (error instanceof Error && error.message) {
      return error.message
    }
    return fallback
  }

  // Computed
  const currentRole = computed(() => {
    return roles.value.find((r) => r.id === currentRoleId.value) || roles.value[0] || null
  })

  const customRoles = computed(() => {
    const defaultIds = DEFAULT_ROLES.map((r) => r.id)
    return roles.value.filter((r) => !defaultIds.includes(r.id))
  })

  const defaultRoles = computed(() => {
    const defaultIds = DEFAULT_ROLES.map((r) => r.id)
    return roles.value.filter((r) => defaultIds.includes(r.id))
  })

  // Actions

  /**
   * Initialize roles with defaults
   */
  async function initializeRoles() {
    try {
      isLoading.value = true
      const state = await fetchRoleState()
      roles.value = state.roles
      currentRoleId.value = state.currentRoleId

      if (roles.value.length === 0) {
        roles.value = [...DEFAULT_ROLES]
        currentRoleId.value = 'default'
        await saveRoles()
        await persistCurrentRoleIdMutation.mutateAsync('default')
      }
    } catch (e) {
      console.error('Failed to initialize roles:', e)
      // Fallback to defaults
      roles.value = [...DEFAULT_ROLES]
      currentRoleId.value = 'default'
    } finally {
      isLoading.value = false
    }
  }

  /**
   * Save roles to storage
   */
  async function saveRoles() {
    try {
      await persistRolesMutation.mutateAsync(roles.value)
    } catch (e) {
      console.error('Failed to save roles:', e)
    }
  }

  /**
   * Select a role
   */
  async function selectRole(roleId: string) {
    const role = roles.value.find((r) => r.id === roleId)
    if (role) {
      currentRoleId.value = roleId
      await persistCurrentRoleIdMutation.mutateAsync(roleId)
    }
  }

  /**
   * Create a new role
   */
  async function createRole(role: Omit<Role, 'id'>): Promise<Role> {
    try {
      isLoading.value = true
      error.value = null

      const id = `role_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`
      const newRole: Role = {
        ...role,
        id,
      }

      roles.value.push(newRole)
      await saveRoles()

      return newRole
    } catch (e: unknown) {
      error.value = getErrorMessage(e, 'Failed to create role')
      throw e
    } finally {
      isLoading.value = false
    }
  }

  /**
   * Update an existing role
   */
  async function updateRole(roleId: string, updates: Partial<Role>) {
    try {
      isLoading.value = true
      error.value = null

      const index = roles.value.findIndex((r) => r.id === roleId)
      if (index === -1) {
        throw new Error('Role not found')
      }

      // Update role properties while preserving ID
      roles.value[index] = {
        ...roles.value[index],
        ...updates,
        id: roleId,
      } as Role

      await saveRoles()
    } catch (e: unknown) {
      error.value = getErrorMessage(e, 'Failed to update role')
      throw e
    } finally {
      isLoading.value = false
    }
  }

  /**
   * Delete a role
   */
  async function deleteRole(roleId: string) {
    try {
      isLoading.value = true
      error.value = null

      // Cannot delete default roles
      const isDefault = DEFAULT_ROLES.some((r) => r.id === roleId)
      if (isDefault) {
        throw new Error('Cannot delete default roles')
      }

      const index = roles.value.findIndex((r) => r.id === roleId)
      if (index === -1) {
        throw new Error('Role not found')
      }

      roles.value.splice(index, 1)

      // If deleted current role, select default
      if (currentRoleId.value === roleId) {
        await selectRole('default')
      }

      await saveRoles()
    } catch (e: unknown) {
      error.value = getErrorMessage(e, 'Failed to delete role')
      throw e
    } finally {
      isLoading.value = false
    }
  }

  /**
   * Reset to default roles
   */
  async function resetToDefaults() {
    roles.value = [...DEFAULT_ROLES]
    currentRoleId.value = 'default'
    await saveRoles()
    await persistCurrentRoleIdMutation.mutateAsync('default')
  }

  return {
    // State
    roles,
    currentRoleId,
    isLoading,
    error,

    // Computed
    currentRole,
    customRoles,
    defaultRoles,

    // Actions
    initializeRoles,
    saveRoles,
    selectRole,
    createRole,
    updateRole,
    deleteRole,
    resetToDefaults,
  }
})
