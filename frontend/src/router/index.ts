/**
 * Vue Router Configuration - Rebuilt with new page structure
 */

import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { pinia } from '@/stores/pinia'

declare module 'vue-router' {
  interface RouteMeta {
    title?: string
    group?: string
    keepAlive?: boolean
    requiresAuth?: boolean
    publicOnly?: boolean
    hideChrome?: boolean
  }
}

// 路由实例。
const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/',
      redirect: '/story/improv',
    },
    {
      path: '/login',
      name: 'login',
      component: () => import('@/views/LoginView.vue'),
      meta: {
        title: '登录',
        publicOnly: true,
        requiresAuth: false,
        hideChrome: true,
      },
    },
    {
      path: '/story',
      redirect: '/story/improv',
    },
    {
      path: '/story/improv',
      name: 'story-improv',
      component: () => import('@/views/StoryView.vue'),
      props: { pageMode: 'improv' },
      meta: { title: '渐进式创作', group: 'features', keepAlive: true },
    },
    {
      path: '/story/scripted',
      name: 'story-scripted',
      component: () => import('@/views/StoryView.vue'),
      props: { pageMode: 'scripted' },
      meta: { title: '剧本主导创作', group: 'features', keepAlive: true },
    },
    {
      path: '/story-adjustment',
      name: 'story-adjustment',
      component: () => import('@/views/StoryAdjustmentView.vue'),
      meta: { title: '故事调整', group: 'features', keepAlive: true },
    },
    // ── Dashboard 类 ─────────────────────────
    {
      path: '/console/models/management',
      name: 'console-model-management',
      component: () => import('@/views/console/ConsoleModelManagementView.vue'),
      meta: { title: '模型管理', group: 'console' },
    },
    {
      path: '/console/models/selection',
      name: 'console-model-selection',
      component: () => import('@/views/console/ConsoleModelSelectionView.vue'),
      meta: { title: '模型选择', group: 'console' },
    },
    {
      path: '/dashboard/lorebook',
      name: 'dashboard-lorebook',
      component: () => import('@/views/DashboardLorebookView.vue'),
      meta: { title: 'Lorebook', group: 'dashboard' },
    },
    {
      path: '/dashboard/scripts',
      name: 'dashboard-scripts',
      component: () => import('@/views/DashboardScriptDesignView.vue'),
      meta: { title: '剧本设计', group: 'dashboard' },
    },
    {
      path: '/dashboard/memory-updates',
      name: 'dashboard-memory-updates',
      component: () => import('@/views/DashboardStoryMemoryView.vue'),
      meta: { title: '记忆变动', group: 'dashboard' },
    },
    {
      path: '/console/analytics/tokens',
      name: 'console-analytics-tokens',
      component: () => import('@/views/console/ConsoleAnalyticsTokensView.vue'),
      meta: { title: 'Token 分析', group: 'console' },
    },
    {
      path: '/console/analytics/overview',
      name: 'console-analytics-overview',
      component: () => import('@/views/console/ConsoleAnalyticsOverviewView.vue'),
      meta: { title: '综合分析', group: 'console' },
    },
    {
      path: '/dashboard/config',
      redirect: '/console/models/management',
    },
    {
      path: '/dashboard/analytics',
      redirect: '/console/analytics/overview',
    },
    {
      path: '/:pathMatch(.*)*',
      redirect: '/story/improv',
    },
  ],
})

router.beforeEach(async (to) => {
  const authStore = useAuthStore(pinia)
  await authStore.ensureResolved()

  document.title = to.meta.title ? `${to.meta.title as string} — 故事工坊` : '故事工坊'

  if (to.meta.publicOnly && authStore.isAuthenticated) {
    const redirect = typeof to.query.redirect === 'string' && to.query.redirect.startsWith('/')
      ? to.query.redirect
      : '/story/improv'
    return redirect
  }

  const requiresAuth = to.meta.requiresAuth ?? !to.meta.publicOnly
  if (requiresAuth && !authStore.isAuthenticated) {
    return {
      name: 'login',
      query: { redirect: to.fullPath },
    }
  }

  return true
})

export default router
