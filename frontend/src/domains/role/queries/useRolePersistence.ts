/**
 * 文件说明：前端业务域逻辑与接口封装。
 */

import { useMutation } from '@tanstack/vue-query'
import { queryClient } from '@/app/queryClient'
import {
  loadRoleState,
  persistRoles,
  persistCurrentRoleId,
  type RolePersistState,
} from '../api/roleStorageApi'

// 变量作用：变量 ROLE_QUERY_KEYS，用于 ROLE QUERY KEYS 相关配置或状态。
export const ROLE_QUERY_KEYS = {
  state: ['role', 'state'] as const,
}

export { type RolePersistState }

/** 功能：函数 fetchRoleState，负责 fetchRoleState 相关处理。 */
export async function fetchRoleState() {
  return queryClient.fetchQuery({
    queryKey: ROLE_QUERY_KEYS.state,
    queryFn: loadRoleState,
    staleTime: 15 * 1000,
  })
}

/** 功能：函数 usePersistRolesMutation，负责 usePersistRolesMutation 相关处理。 */
export function usePersistRolesMutation() {
  return useMutation({
    mutationFn: persistRoles,
    onSuccess: (roles) => {
      const previous = queryClient.getQueryData<RolePersistState>(ROLE_QUERY_KEYS.state)
      queryClient.setQueryData(ROLE_QUERY_KEYS.state, {
        roles,
        currentRoleId: previous?.currentRoleId || roles[0]?.id || 'default',
      })
    },
  })
}

/** 功能：函数 usePersistCurrentRoleIdMutation，负责 usePersistCurrentRoleIdMutation 相关处理。 */
export function usePersistCurrentRoleIdMutation() {
  return useMutation({
    mutationFn: persistCurrentRoleId,
    onSuccess: (currentRoleId) => {
      const previous = queryClient.getQueryData<RolePersistState>(ROLE_QUERY_KEYS.state)
      queryClient.setQueryData(ROLE_QUERY_KEYS.state, {
        roles: previous?.roles || [],
        currentRoleId,
      })
    },
  })
}