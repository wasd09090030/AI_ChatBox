<script setup lang="ts">
// 文件说明：前端页面级视图编排。
import AnalyticsEventsTable from '@/domains/analytics/components/AnalyticsEventsTable.vue'
import AnalyticsHeader from '@/domains/analytics/components/AnalyticsHeader.vue'
import AnalyticsInsightPanel from '@/domains/analytics/components/AnalyticsInsightPanel.vue'
import AnalyticsMetricGrid from '@/domains/analytics/components/AnalyticsMetricGrid.vue'
import AnalyticsStoryMemoryPanel from '@/domains/analytics/components/AnalyticsStoryMemoryPanel.vue'
import EventTypeDistributionChart from '@/domains/analytics/components/charts/EventTypeDistributionChart.vue'
import LatencyTrendChart from '@/domains/analytics/components/charts/LatencyTrendChart.vue'
import ModelDistributionChart from '@/domains/analytics/components/charts/ModelDistributionChart.vue'
import RequestsTrendChart from '@/domains/analytics/components/charts/RequestsTrendChart.vue'
import WorldDistributionChart from '@/domains/analytics/components/charts/WorldDistributionChart.vue'
import { useConsoleAnalyticsState } from '@/domains/analytics/composables/useConsoleAnalyticsState'

const {
  days,
  selectedModel,
  selectedWorldId,
  selectedEventType,
  overview,
  daily,
  events,
  overviewLoading,
  dailyLoading,
  eventsLoading,
  refreshing,
  worldLabelMap,
  modelDistributionItems,
  eventTypeDistributionItems,
  worldDistributionItems,
  modelOptions,
  worldOptions,
  eventTypeOptions,
  topModelLabel,
  topWorldLabel,
  overviewMetrics,
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
      eyebrow="控制台 / 总览"
      title="综合分析"
      description="把请求成功率、响应速度、世界命中和事件分布放在一起看，定位运行质量与内容偏移问题。"
      @update:days="days = $event"
      @update:model="selectedModel = $event"
      @update:world-id="selectedWorldId = $event"
      @update:event-type="selectedEventType = $event"
      @refresh="refetchAll"
    />

    <div class="flex-1 space-y-5 px-6 py-5">
      <AnalyticsMetricGrid :metrics="overviewMetrics" />

      <AnalyticsInsightPanel
        :overview="overview"
        :top-model-label="topModelLabel"
        :top-world-label="topWorldLabel"
      />

      <div class="grid gap-4 xl:grid-cols-2">
        <RequestsTrendChart :points="daily ?? []" :loading="dailyLoading" />
        <LatencyTrendChart :points="daily ?? []" :loading="dailyLoading" />
      </div>

      <div class="grid gap-4 xl:grid-cols-3">
        <ModelDistributionChart :items="modelDistributionItems" :loading="overviewLoading" />
        <WorldDistributionChart :items="worldDistributionItems" :loading="overviewLoading" />
        <EventTypeDistributionChart :items="eventTypeDistributionItems" :loading="overviewLoading" />
      </div>

      <div class="grid gap-4 xl:grid-cols-[minmax(0,2fr)_minmax(320px,1fr)]">
        <AnalyticsEventsTable
          :events="events ?? []"
          :loading="eventsLoading"
          :world-label-map="worldLabelMap"
        />
        <AnalyticsStoryMemoryPanel />
      </div>
    </div>
  </div>
</template>
