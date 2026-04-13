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

// 常量 ROLE_QUERY_KEYS。
export const ROLE_QUERY_KEYS = {
  state: ['role', 'state'] as const,
}

export { type RolePersistState }

/** 处理 fetchRoleState 相关逻辑。 */
export async function fetchRoleState() {
  return queryClient.fetchQuery({
    queryKey: ROLE_QUERY_KEYS.state,
    queryFn: loadRoleState,
    staleTime: 15 * 1000,
  })
}

/** 处理 usePersistRolesMutation 相关逻辑。 */
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

/** 处理 usePersistCurrentRoleIdMutation 相关逻辑。 */
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