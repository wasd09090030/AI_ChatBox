/**
 * 文件说明：前端业务域逻辑与接口封装。
 */

import { storage } from '@/utils/storage'
import { DEFAULT_ROLES } from '@/utils/constants'
import type { Role } from '@/utils/types'

export type RolePersistState = {
  roles: Role[]
  currentRoleId: string
}

// 变量作用：变量 ROLE_STORAGE_KEYS，用于 ROLE STORAGE KEYS 相关配置或状态。
export const ROLE_STORAGE_KEYS = {
  roles: 'roles',
  currentRoleId: 'currentRoleId',
} as const

/** 功能：函数 loadRoleState，负责 loadRoleState 相关处理。 */
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

/** 功能：函数 persistRoles，负责 persistRoles 相关处理。 */
export async function persistRoles(roles: Role[]) {
  await storage.setStorage(ROLE_STORAGE_KEYS.roles, JSON.stringify(roles))
  return roles
}

/** 功能：函数 persistCurrentRoleId，负责 persistCurrentRoleId 相关处理。 */
export async function persistCurrentRoleId(roleId: string) {
  await storage.setStorage(ROLE_STORAGE_KEYS.currentRoleId, roleId)
  return roleId
}