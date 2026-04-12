/**
 * 文件说明：项目文件 queryClient.ts 的核心逻辑实现。
 */

import { QueryClient } from '@tanstack/vue-query'

// 变量作用：变量 queryClient，用于 queryClient 相关配置或状态。
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
