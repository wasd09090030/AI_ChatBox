<script setup lang="ts">
// 文件说明：项目文件 App.vue 的核心逻辑实现。
import AppSidebar from '@/components/layout/AppSidebar.vue'
import { Toaster } from '@/components/ui/toast'
import { queryClient } from '@/app/queryClient'
import { RouterView } from 'vue-router'
import { computed, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { useConfigStore } from '@/stores/config'
import { useStorySessionStore } from '@/stores/storySession'
import { useAuthStore } from '@/stores/auth'
import { storage } from '@/utils/storage'

// configStore 状态仓库实例。
const configStore = useConfigStore()
// storySessionStore 状态仓库实例。
const storySessionStore = useStorySessionStore()
const authStore = useAuthStore()
const route = useRoute()
const isWorkspaceBootstrapping = ref(false)
let bootstrapToken = 0

const showSidebar = computed(() => authStore.isAuthenticated && !route.meta.hideChrome)
const showWorkspaceLoader = computed(() => (
  authStore.isResolved &&
  authStore.isAuthenticated &&
  isWorkspaceBootstrapping.value &&
  !route.meta.hideChrome
))

watch(
  () => authStore.user?.user_id ?? null,
  async (userId, previousUserId) => {
    if (!authStore.isResolved) {
      return
    }

    const hasUserChanged = previousUserId !== undefined && previousUserId !== userId
    if (hasUserChanged) {
      queryClient.clear()
      configStore.resetSessionState()
      storySessionStore.resetSessionState()
    }

    if (!userId) {
      storage.setUserScope(null)
      isWorkspaceBootstrapping.value = false
      return
    }

    const currentToken = ++bootstrapToken
    isWorkspaceBootstrapping.value = true
    storage.setUserScope(userId)

    try {
      await configStore.initializeConfig()
      await storySessionStore.loadFromStorage()
    } finally {
      if (bootstrapToken === currentToken) {
        isWorkspaceBootstrapping.value = false
      }
    }
  },
  { immediate: true },
)
</script>

<template>
  <div class="flex h-screen w-screen overflow-hidden bg-background text-foreground">
    <!-- Left Sidebar -->
    <AppSidebar v-if="showSidebar" />

    <!-- Main Content Area -->
    <main class="flex-1 overflow-hidden flex flex-col min-w-0">
      <div
        v-if="showWorkspaceLoader"
        class="flex h-full items-center justify-center bg-background/80 px-6 text-center"
      >
        <div class="max-w-sm space-y-3">
          <p class="text-xs uppercase tracking-[0.32em] text-muted-foreground">
            Workspace Restore
          </p>
          <h1 class="text-2xl font-semibold text-foreground">
            正在整理你的编辑台
          </h1>
          <p class="text-sm leading-6 text-muted-foreground">
            会话、配置和跨设备同步状态正在按当前账号恢复。
          </p>
        </div>
      </div>
      <RouterView v-else v-slot="{ Component, route }">
        <KeepAlive>
          <component :is="Component" v-if="route.meta.keepAlive" :key="String(route.name)" />
        </KeepAlive>
        <component :is="Component" v-if="!route.meta.keepAlive" />
      </RouterView>
    </main>

    <!-- Toast notifications -->
    <Toaster />
  </div>
</template>
