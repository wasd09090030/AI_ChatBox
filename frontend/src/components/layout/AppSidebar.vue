<script setup lang="ts">
// 文件说明：前端可复用界面组件。
import { useRoute, RouterLink } from 'vue-router'
import {
  BookOpen,
  Settings,
  Library,
  ScrollText,
  FilePenLine,
  ChevronDown,
  ChevronsLeft,
  ChevronsRight,
  Gauge,
  Coins,
  History,
  BrainCircuit,
} from 'lucide-vue-next'
import { ref } from 'vue'
import { cn } from '@/lib/utils'
import { useSidebarCollapse } from '@/lib/useSidebarCollapse'

// 当前路由对象。
const route = useRoute()

// featureGroupOpen 相关状态。
const featureGroupOpen = ref(true)
// dashboardGroupOpen 相关状态。
const dashboardGroupOpen = ref(true)
// consoleGroupOpen 相关状态。
const consoleGroupOpen = ref(true)
// sidebarCollapsed 相关状态。
const sidebarCollapsed = useSidebarCollapse('app-sidebar-collapsed')

interface NavItem {
  path: string
  label: string
  icon: any
}

const featureItems: NavItem[] = [
  { path: '/story/improv', label: '渐进式创作', icon: BookOpen },
  { path: '/story/scripted', label: '严格剧本创作', icon: ScrollText },
  { path: '/story-adjustment', label: '故事调整', icon: FilePenLine },
]

const dashboardItems: NavItem[] = [
  { path: '/dashboard/lorebook', label: 'Lorebook', icon: Library },
  { path: '/dashboard/scripts', label: '剧本设计', icon: ScrollText },
  { path: '/dashboard/memory-updates', label: '记忆变动', icon: History },
]

const consoleItems: NavItem[] = [
  { path: '/console/analytics/overview', label: '综合分析', icon: Gauge },
  { path: '/console/analytics/tokens', label: 'Token 分析', icon: Coins },
  { path: '/console/models/management', label: '模型管理', icon: Settings },
  { path: '/console/models/selection', label: '模型选择', icon: BrainCircuit },
]

// navGroups 相关状态。
const navGroups = [
  { key: 'feature', label: '功能', open: featureGroupOpen, items: featureItems },
  { key: 'dashboard', label: '管理', open: dashboardGroupOpen, items: dashboardItems },
  { key: 'console', label: '控制台', open: consoleGroupOpen, items: consoleItems },
]

/** 处理 isActive 相关逻辑。 */
function isActive(path: string): boolean {
  return route.path === path || route.path.startsWith(path + '/')
}
</script>

<template>
  <aside
    :class="
      cn(
        'flex h-screen shrink-0 flex-col overflow-hidden border-r border-border bg-sidebar text-sidebar-foreground transition-[width] duration-200',
        sidebarCollapsed ? 'w-16' : 'w-56',
      )
    "
  >
    <!-- Logo / Brand -->
    <div
      :class="
        cn(
          'flex h-14 items-center border-b border-sidebar-border shrink-0',
          sidebarCollapsed ? 'justify-center px-2' : 'gap-3 px-4',
        )
      "
    >
      <div class="w-7 h-7 rounded-md bg-primary flex items-center justify-center shrink-0">
        <BookOpen class="w-4 h-4 text-primary-foreground" />
      </div>
      <span v-if="!sidebarCollapsed" class="font-semibold text-sm tracking-tight">故事工坊</span>
    </div>

    <!-- Navigation -->
    <nav class="flex-1 overflow-y-auto py-3 px-2 space-y-1 scrollbar-thin">
      <div v-for="(group, index) in navGroups" :key="group.key">
        <button
          v-if="!sidebarCollapsed"
          class="flex items-center justify-between w-full px-2 py-1.5 text-xs font-medium text-muted-foreground uppercase tracking-wider hover:text-foreground transition-colors"
          @click="group.open.value = !group.open.value"
        >
          <span>{{ group.label }}</span>
          <ChevronDown
            class="w-3 h-3 transition-transform duration-200"
            :class="{ 'rotate-180': !group.open.value }"
          />
        </button>

        <div
          v-show="sidebarCollapsed || group.open.value"
          :class="sidebarCollapsed ? 'space-y-1' : 'mt-1 space-y-0.5'"
        >
          <RouterLink
            v-for="item in group.items"
            :key="item.path"
            :to="item.path"
            :title="sidebarCollapsed ? item.label : undefined"
            :class="cn(
              'flex rounded-md text-sm font-medium transition-colors',
              isActive(item.path)
                ? 'bg-sidebar-accent text-sidebar-accent-foreground'
                : 'text-sidebar-foreground hover:bg-sidebar-accent/60 hover:text-sidebar-accent-foreground',
              sidebarCollapsed ? 'justify-center px-2 py-2.5' : 'items-center gap-2.5 px-2 py-2',
            )"
          >
            <component :is="item.icon" class="w-4 h-4 shrink-0" />
            <span v-if="!sidebarCollapsed" class="truncate">{{ item.label }}</span>
          </RouterLink>
        </div>

        <div
          v-if="index < navGroups.length - 1"
          :class="cn('h-px bg-sidebar-border my-2', sidebarCollapsed ? 'mx-1' : 'mx-2')"
        />
      </div>
    </nav>

    <!-- Footer -->
    <div :class="cn('border-t border-sidebar-border shrink-0', sidebarCollapsed ? 'px-2 py-2' : 'px-4 py-3')">
      <button
        :title="sidebarCollapsed ? '展开侧边栏' : '收起侧边栏'"
        :class="
          cn(
            'flex w-full items-center rounded-md text-sm text-muted-foreground transition-colors hover:bg-sidebar-accent/60 hover:text-sidebar-accent-foreground',
            sidebarCollapsed ? 'justify-center px-0 py-2' : 'gap-2 px-2 py-2',
          )
        "
        @click="sidebarCollapsed = !sidebarCollapsed"
      >
        <component :is="sidebarCollapsed ? ChevronsRight : ChevronsLeft" class="w-4 h-4 shrink-0" />
        <span v-if="!sidebarCollapsed">收起侧边栏</span>
      </button>
      <p v-if="!sidebarCollapsed" class="mt-2 text-xs text-muted-foreground">v2.0 · 故事工坊</p>
    </div>
  </aside>
</template>
