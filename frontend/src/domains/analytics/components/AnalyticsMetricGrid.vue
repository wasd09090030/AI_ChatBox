<script setup lang="ts">
// 文件说明：前端业务域逻辑与接口封装。
import {
  Clock3, Database, Gauge, Hash, ShieldCheck, TriangleAlert, Waypoints, Waves,
} from 'lucide-vue-next'
import type { AnalyticsMetricItem } from '@/domains/analytics/types'

// 组件输入参数。
const props = defineProps<{
  metrics: AnalyticsMetricItem[]
}>()

// iconMap 相关状态。
const iconMap = {
  requests: Hash,
  success: ShieldCheck,
  errors: TriangleAlert,
  inputTokens: Waves,
  outputTokens: Gauge,
  avgTokens: Hash,
  latency: Clock3,
  retrieval: Database,
} as const

// accentClassMap 相关状态。
const accentClassMap = {
  default: 'text-foreground',
  success: 'text-emerald-600 dark:text-emerald-400',
  danger: 'text-rose-600 dark:text-rose-400',
  warning: 'text-amber-600 dark:text-amber-400',
  info: 'text-sky-600 dark:text-sky-400',
}
</script>

<template>
  <section class="grid grid-cols-2 gap-3 xl:grid-cols-4">
    <article
      v-for="metric in props.metrics"
      :key="metric.key"
      class="rounded-2xl border border-border bg-card/80 p-4 shadow-sm shadow-black/5"
    >
      <div class="mb-3 flex items-center gap-2 text-xs text-muted-foreground">
        <component :is="iconMap[metric.key]" class="h-4 w-4" />
        <span>{{ metric.label }}</span>
      </div>
      <div class="flex items-end justify-between gap-3">
        <p class="text-2xl font-semibold tracking-tight" :class="accentClassMap[metric.accent ?? 'default']">
          {{ metric.value }}
        </p>
        <Waypoints v-if="metric.key === 'retrieval'" class="h-4 w-4 text-muted-foreground/60" />
      </div>
      <p v-if="metric.caption" class="mt-2 text-xs leading-5 text-muted-foreground">{{ metric.caption }}</p>
    </article>
  </section>
</template>
