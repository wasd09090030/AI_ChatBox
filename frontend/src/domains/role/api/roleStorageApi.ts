import { storage } from '@/utils/storage'
import { DEFAULT_ROLES } from '@/utils/constants'
import type { Role } from '@/utils/types'

export type RolePersistState = {
  roles: Role[]
  currentRoleId: string
}

export const ROLE_STORAGE_KEYS = {
  roles: 'roles',
  currentRoleId: 'currentRoleId',
} as const

export async function loadRoleState(): Promise<RolePersistState> {
  let storedRoles = await storage.getStorage(ROLE_STORAGE_KEYS.roles)
  if (!storedRoles) storedRoles = await storage.pullFromRemote(ROLE_STORAGE_KEYS.roles)
  const roles: Role[] = storedRoles ? JSON.parse(storedRoles) : [...DEFAULT_ROLES]

  let storedRoleId = await storage.getStorage(ROLE_STORAGE_KEYS.currentRoleId)
  if (!storedRoleId) storedRoleId = await storage.pullFromRemote(ROLE_STORAGE_KEYS.currentRoleId)
  const currentRoleId =
    storedRoleId && roles.some((role) => role.id === storedRoleId)
      ? storedRoleId
      : roles[0]?.id || 'default'

  return { roles, currentRoleId }
}

export async function persistRoles(roles: Role[]) {
  await storage.setStorage(ROLE_STORAGE_KEYS.roles, JSON.stringify(roles))
  return roles
}

export async function persistCurrentRoleId(roleId: string) {
  await storage.setStorage(ROLE_STORAGE_KEYS.currentRoleId, roleId)
  return roleId
}