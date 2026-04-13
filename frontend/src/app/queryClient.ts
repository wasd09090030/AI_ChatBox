/**
 * 文件说明：项目文件 queryClient.ts 的核心逻辑实现。
 */

import { QueryClient } from '@tanstack/vue-query'

// TanStack Query 客户端实例。
export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30 * 1000,
      gcTime: 5 * 60 * 1000,
      refetchOnWindowFocus: false,
      retry: 1,
    },
    mutations: {
      retry: 0,
    },
  },
})
