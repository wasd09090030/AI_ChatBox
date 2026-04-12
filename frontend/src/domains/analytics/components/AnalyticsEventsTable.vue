<script setup lang="ts">
// 文件说明：前端业务域逻辑与接口封装。
import { Activity } from 'lucide-vue-next'
import { computed, ref, watch } from 'vue'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import type { AnalyticsEvent } from '@/domains/analytics/types'
import { formatSeconds, formatTimestamp, resolveWorldLabel } from '@/domains/analytics/utils/formatters'

// 变量作用：变量 props，用于 props 相关配置或状态。
const props = defineProps<{
  events: AnalyticsEvent[]
  loading?: boolean
  worldLabelMap: Record<string, string>
}>()

/** 功能：函数 getTotalTokens，负责 getTotalTokens 相关处理。 */
function getTotalTokens(event: AnalyticsEvent): number {
  return event.total_tokens ?? event.total_tokens_est ?? 0
}

// 变量作用：变量 PAGE_SIZE，用于 PAGE SIZE 相关配置或状态。
const PAGE_SIZE = 20
// 变量作用：变量 currentPage，用于 currentPage 相关配置或状态。
const currentPage = ref(1)

// 变量作用：变量 totalPages，用于 totalPages 相关配置或状态。
const totalPages = computed(() => Math.max(1, Math.ceil(props.events.length / PAGE_SIZE)))
// 变量作用：变量 pagedEvents，用于 pagedEvents 相关配置或状态。
const pagedEvents = computed(() => {
  const start = (currentPage.value - 1) * PAGE_SIZE
  return props.events.slice(start, start + PAGE_SIZE)
})

watch(
  () => props.events.length,
  () => {
    currentPage.value = 1
  },
)

/** 功能：函数 goToPreviousPage，负责 goToPreviousPage 相关处理。 */
function goToPreviousPage() {
  currentPage.value = Math.max(1, currentPage.value - 1)
}

/** 功能：函数 goToNextPage，负责 goToNextPage 相关处理。 */
function goToNextPage() {
  currentPage.value = Math.min(totalPages.value, currentPage.value + 1)
}
</script>

<template>
  <section class="overflow-hidden rounded-2xl border border-border bg-card/80 shadow-sm shadow-black/5">
    <div class="flex items-center justify-between border-b border-border bg-muted/20 px-4 py-3">
      <div class="flex items-center gap-2">
        <Activity class="h-3.5 w-3.5 text-muted-foreground" />
        <h3 class="text-sm font-semibold">最近请求明细</h3>
      </div>
      <p class="text-xs text-muted-foreground">每页 20 条，保留时间、类型、世界、模型、总消耗、耗时和状态，便于快速筛查异常请求。</p>
    </div>

    <div v-if="loading" class="py-10 text-center text-sm text-muted-foreground">加载中…</div>
    <div v-else-if="!events.length" class="py-10 text-center text-sm text-muted-foreground">暂无记录</div>
    <div v-else class="overflow-x-auto">
      <table class="min-w-full text-xs">
        <thead>
          <tr class="border-b border-border bg-muted/10 text-muted-foreground">
            <th class="px-4 py-3 text-left font-medium">时间</th>
            <th class="px-4 py-3 text-left font-medium">类型</th>
            <th class="px-4 py-3 text-left font-medium">世界</th>
            <th class="px-4 py-3 text-left font-medium">模型</th>
            <th class="px-4 py-3 text-right font-medium">Token</th>
            <th class="px-4 py-3 text-right font-medium">耗时</th>
            <th class="px-4 py-3 text-center font-medium">状态</th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="(event, index) in pagedEvents"
            :key="`${event.timestamp}-${index}`"
            class="border-b border-border last:border-0 hover:bg-muted/20"
          >
            <td class="whitespace-nowrap px-4 py-3 tabular-nums text-muted-foreground">{{ formatTimestamp(event.timestamp) }}</td>
            <td class="px-4 py-3"><Badge variant="secondary" class="font-mono text-[10px]">{{ event.event_type }}</Badge></td>
            <td class="px-4 py-3 text-muted-foreground">{{ resolveWorldLabel(event.world_id, props.worldLabelMap) }}</td>
            <td class="px-4 py-3 font-mono text-muted-foreground">{{ event.model || '–' }}</td>
            <td class="px-4 py-3 text-right tabular-nums font-semibold">{{ getTotalTokens(event) }}</td>
            <td class="px-4 py-3 text-right tabular-nums text-muted-foreground">{{ formatSeconds(event.generation_time ?? 0) }}</td>
            <td class="px-4 py-3 text-center">
              <Badge :variant="event.success ? 'default' : 'destructive'" class="text-[10px]">
                {{ event.success ? '成功' : event.error_type || '失败' }}
              </Badge>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
    <div v-if="events.length" class="flex items-center justify-between border-t border-border bg-muted/10 px-4 py-3">
      <p class="text-xs text-muted-foreground">
        第 {{ currentPage }} / {{ totalPages }} 页，共 {{ events.length }} 条
      </p>
      <div class="flex items-center gap-2">
        <Button variant="outline" size="sm" class="h-8 px-3 text-xs" :disabled="currentPage <= 1" @click="goToPreviousPage">
          上一页
        </Button>
        <Button variant="outline" size="sm" class="h-8 px-3 text-xs" :disabled="currentPage >= totalPages" @click="goToNextPage">
          下一页
        </Button>
      </div>
    </div>
  </section>
</template>
