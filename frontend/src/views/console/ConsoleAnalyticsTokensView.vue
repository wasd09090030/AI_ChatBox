<script setup lang="ts">
import AnalyticsHeader from '@/domains/analytics/components/AnalyticsHeader.vue'
import AnalyticsMetricGrid from '@/domains/analytics/components/AnalyticsMetricGrid.vue'
import TokenBreakdownTrendChart from '@/domains/analytics/components/charts/TokenBreakdownTrendChart.vue'
import TokenSourceShareChart from '@/domains/analytics/components/charts/TokenSourceShareChart.vue'
import ModelDistributionChart from '@/domains/analytics/components/charts/ModelDistributionChart.vue'
import { useConsoleAnalyticsState } from '@/domains/analytics/composables/useConsoleAnalyticsState'

const {
  days,
  selectedModel,
  selectedWorldId,
  selectedEventType,
  daily,
  overviewLoading,
  dailyLoading,
  refreshing,
  modelDistributionItems,
  tokenSourceDistributionItems,
  modelOptions,
  worldOptions,
  eventTypeOptions,
  tokenMetrics,
  refetchAll,
} = useConsoleAnalyticsState()
</script>

<template>
  <div class="flex h-full flex-col overflow-y-auto bg-background">
    <AnalyticsHeader
      :days="days"
      :refreshing="refreshing"
      :selected-model="selectedModel"
      :selected-world-id="selectedWorldId"
      :selected-event-type="selectedEventType"
      :model-options="modelOptions"
      :world-options="worldOptions"
      :event-type-options="eventTypeOptions"
      eyebrow="控制台 / Token"
      title="Token 分析"
      description="聚焦输入、输出、总消耗与统计来源，快速判断当前创作链路的 token 成本是否健康。"
      @update:days="days = $event"
      @update:model="selectedModel = $event"
      @update:world-id="selectedWorldId = $event"
      @update:event-type="selectedEventType = $event"
      @refresh="refetchAll"
    />

    <div class="flex-1 space-y-5 px-6 py-5">
      <AnalyticsMetricGrid :metrics="tokenMetrics" />

      <div class="grid gap-4 xl:grid-cols-2">
        <TokenBreakdownTrendChart :points="daily ?? []" :loading="dailyLoading" />
        <TokenSourceShareChart :items="tokenSourceDistributionItems" :loading="overviewLoading" />
      </div>

      <div class="grid gap-4 xl:grid-cols-2">
        <ModelDistributionChart :items="modelDistributionItems" :loading="overviewLoading" />
        <div class="rounded-2xl border border-border bg-card p-5">
          <p class="text-sm font-medium text-foreground">读数说明</p>
          <div class="mt-3 space-y-3 text-sm leading-6 text-muted-foreground">
            <p>Token 页只看消耗，不混入请求失败、世界分布等其它信号，方便快速识别哪类模型和场景最费成本。</p>
            <p>如果 `Provider 真实用量` 占比偏低，说明更多数据来自估算值，读数适合趋势判断，不适合做精确成本核算。</p>
            <p>若单次总消耗持续抬升，优先检查模型切换、Prompt 强化、上下文命中数量和世界设定注入策略。</p>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
