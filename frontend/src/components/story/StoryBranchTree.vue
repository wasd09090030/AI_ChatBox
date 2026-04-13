<script setup lang="ts">
/**
 * StoryBranchTree
 *
 * Visualizes the story exploration tree using ECharts Tree chart.
 * Interaction model: CLICK a node to pin its details in the side panel.
 * (Hover-based interaction was removed because it caused layout-shift → autoresize → rerender loops.)
 */
import { computed, watch, ref } from 'vue'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { TreeChart } from 'echarts/charts'
import { TooltipComponent, TitleComponent } from 'echarts/components'
import VChart from 'vue-echarts'
import { GitBranch, X, Info } from 'lucide-vue-next'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { useStorySessionStore } from '@/stores/storySession'

use([CanvasRenderer, TreeChart, TooltipComponent, TitleComponent])

// 组件输入参数。
const props = defineProps<{
  storyId: string
  storyTitle?: string
}>()

// 组件事件派发器。
const emit = defineEmits<{
  (e: 'close'): void
}>()

// 状态仓库实例。
const store = useStorySessionStore()

// ── Selected node (click-based, NOT hover) ────────────────────────────────────
const selectedNode = ref<{
  prompt: string
  contentPreview: string
  isOnActivePath: boolean
} | null>(null)

// ── ECharts option ────────────────────────────────────────────────────────────
const chartOption = computed(() => {
  const treeData = store.buildEChartsTree(props.storyId)
  if (!treeData) return null

  return {
    backgroundColor: 'transparent',
    tooltip: {
      trigger: 'item',
      triggerOn: 'mousemove',
      // Tooltip renders inside the canvas overlay — no layout impact
      formatter: (params: Record<string, unknown>) => {
        const d = params.data as Record<string, unknown>
        if (!d) return ''
        const prompt = (d.prompt as string) ?? ''
        const preview = (d.contentPreview as string) ?? ''
        const active = d.isOnActivePath as boolean
        const badge = active ? '🟢 活跃路径' : '⬜ 已回滚'
        return `
          <div style="max-width:240px;font-size:12px;line-height:1.6">
            <div style="font-weight:600;margin-bottom:4px;color:#e2e8f0">${badge}</div>
            <div style="color:#94a3b8;margin-bottom:4px">玩家输入：</div>
            <div style="color:#f1f5f9;margin-bottom:6px">${prompt}</div>
            ${preview ? `<div style="color:#94a3b8;margin-bottom:2px">AI 回复预览：</div><div style="color:#cbd5e1;font-style:italic">${preview}</div>` : ''}
            <div style="margin-top:8px;color:#64748b;font-size:11px">点击节点固定详情</div>
          </div>
        `
      },
      backgroundColor: '#1e293b',
      borderColor: '#334155',
      borderWidth: 1,
      padding: [10, 14],
      confine: true,
    },
    series: [
      {
        type: 'tree',
        data: [treeData],
        top: '8%',
        left: '12%',
        bottom: '8%',
        right: '12%',
        symbolSize: 14,
        symbol: 'circle',
        orient: 'TB',
        expandAndCollapse: false,
        edgeShape: 'curve',
        label: {
          show: true,
          position: 'bottom',
          distance: 8,
          fontSize: 11,
          fontFamily: 'ui-sans-serif, system-ui, sans-serif',
        },
        leaves: {
          label: {
            position: 'bottom',
            distance: 8,
          },
        },
        lineStyle: {
          color: '#334155',
          width: 1.5,
          curveness: 0.5,
        },
        emphasis: {
          focus: 'ancestor',
          lineStyle: { width: 3 },
        },
        animationDuration: 300,
        animationDurationUpdate: 250,
      },
    ],
  }
})

// 布尔状态 hasData。
const hasData = computed(() => {
  const tree = store.getBranchTree(props.storyId)
  return tree && tree.rootNodeId !== null
})

// ── Click handler — no layout change, no jitter ───────────────────────────────
function onNodeClick(params: Record<string, unknown>) {
  // Only respond to series node clicks, not line/label clicks
  if (params.componentType !== 'series') return
  const d = params.data as Record<string, unknown> | undefined
  if (!d || !d.prompt) return

  // Toggle: clicking the same node again dismisses the panel
  if (
    selectedNode.value?.prompt === (d.prompt as string) &&
    selectedNode.value?.contentPreview === (d.contentPreview as string)
  ) {
    selectedNode.value = null
    return
  }
  selectedNode.value = {
    prompt: (d.prompt as string) ?? '',
    contentPreview: (d.contentPreview as string) ?? '',
    isOnActivePath: (d.isOnActivePath as boolean) ?? false,
  }
}

watch(() => props.storyId, () => {
  selectedNode.value = null
})
</script>

<template>
  <div class="flex flex-col h-full bg-background/95 backdrop-blur-sm">
    <!-- Header -->
    <div class="flex items-center justify-between px-4 py-3 border-b border-border shrink-0">
      <div class="flex items-center gap-2">
        <GitBranch class="h-4 w-4 text-primary" />
        <span class="text-sm font-semibold">故事分支树</span>
        <Badge v-if="storyTitle" variant="secondary" class="text-[10px]">{{ storyTitle }}</Badge>
      </div>
      <Button size="icon" variant="ghost" class="h-7 w-7" @click="emit('close')">
        <X class="h-4 w-4" />
      </Button>
    </div>

    <!-- Empty state -->
    <div
      v-if="!hasData"
      class="flex-1 flex flex-col items-center justify-center text-center gap-3 text-muted-foreground p-8"
    >
      <GitBranch class="h-12 w-12 opacity-20" />
      <p class="text-sm font-medium">暂无分支数据</p>
      <p class="text-xs opacity-70">在 choices 模式下开始故事后，这里将生成交互式分支树</p>
    </div>

    <!-- Chart + legend -->
    <template v-else>
      <!-- Legend -->
      <div class="flex items-center gap-4 px-4 py-2 border-b border-border/50 shrink-0 text-xs text-muted-foreground">
        <div class="flex items-center gap-1.5">
          <span class="h-3 w-3 rounded-full bg-orange-500 shrink-0" />
          当前节点
        </div>
        <div class="flex items-center gap-1.5">
          <span class="h-3 w-3 rounded-full bg-blue-500 shrink-0" />
          活跃路径
        </div>
        <div class="flex items-center gap-1.5">
          <span class="h-3 w-3 rounded-full bg-slate-400 shrink-0" />
          已回滚
        </div>
        <div class="ml-auto flex items-center gap-1 opacity-60">
          <Info class="h-3 w-3" />
          点击节点固定详情
        </div>
      </div>

      <div class="flex-1 flex min-h-0">
        <!-- ECharts tree — click triggers node detail, NOT hover (avoids autoresize jitter) -->
        <VChart
          class="flex-1"
          :option="chartOption!"
          autoresize
          @click="onNodeClick"
        />

        <!-- Node detail panel (appears on click, dismisses on second click) -->
        <transition
          enter-active-class="transition-all duration-150"
          enter-from-class="opacity-0 translate-x-3"
          enter-to-class="opacity-100 translate-x-0"
          leave-active-class="transition-all duration-100"
          leave-from-class="opacity-100 translate-x-0"
          leave-to-class="opacity-0 translate-x-3"
        >
          <div
            v-if="selectedNode"
            class="w-56 shrink-0 border-l border-border p-4 space-y-3 overflow-y-auto"
          >
            <div class="flex items-center justify-between">
              <p class="text-xs font-semibold text-muted-foreground uppercase tracking-wide">节点详情</p>
              <Button size="icon" variant="ghost" class="h-5 w-5 -mr-1" @click="selectedNode = null">
                <X class="h-3 w-3" />
              </Button>
            </div>

            <div>
              <p class="text-[10px] text-muted-foreground mb-1">玩家输入</p>
              <p class="text-sm text-foreground leading-relaxed">{{ selectedNode.prompt }}</p>
            </div>

            <div v-if="selectedNode.contentPreview">
              <p class="text-[10px] text-muted-foreground mb-1">AI 回复预览</p>
              <p class="text-xs text-muted-foreground leading-relaxed italic line-clamp-6">{{ selectedNode.contentPreview }}</p>
            </div>

            <Badge
              :variant="selectedNode.isOnActivePath ? 'default' : 'secondary'"
              class="text-[10px]"
            >
              {{ selectedNode.isOnActivePath ? '活跃路径' : '已回滚' }}
            </Badge>
          </div>
        </transition>
      </div>
    </template>
  </div>
</template>
