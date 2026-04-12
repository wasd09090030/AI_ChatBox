<script setup lang="ts">
// 文件说明：项目文件 App.vue 的核心逻辑实现。
import AppSidebar from '@/components/layout/AppSidebar.vue'
import { Toaster } from '@/components/ui/toast'
import { RouterView } from 'vue-router'
import { onMounted } from 'vue'
import { useConfigStore } from '@/stores/config'
import { useStorySessionStore } from '@/stores/storySession'

// 变量作用：变量 configStore，用于 configStore 相关配置或状态。
const configStore = useConfigStore()
// 变量作用：变量 storySessionStore，用于 storySessionStore 相关配置或状态。
const storySessionStore = useStorySessionStore()

onMounted(async () => {
  // Load config/API keys (existing)
  await configStore.initializeConfig()
  // Hydrate story session state from backend (cross-device sync)
  await storySessionStore.loadFromStorage()
})
</script>

<template>
  <div class="flex h-screen w-screen overflow-hidden bg-background text-foreground">
    <!-- Left Sidebar -->
    <AppSidebar />

    <!-- Main Content Area -->
    <main class="flex-1 overflow-hidden flex flex-col min-w-0">
      <RouterView v-slot="{ Component, route }">
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
