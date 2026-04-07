<script setup lang="ts">
import { computed } from 'vue'
import type { EChartsOption } from 'echarts'
import VChart from 'vue-echarts'
import '@/domains/analytics/lib/registerCharts'
import AnalyticsChartCard from '@/domains/analytics/components/AnalyticsChartCard.vue'
import type { AnalyticsDailyStat } from '@/domains/analytics/types'

const props = defineProps<{
  points: AnalyticsDailyStat[]
  loading?: boolean
}>()

const hasData = computed(() => props.points.length > 0)

const option = computed<EChartsOption>(() => ({
  tooltip: { trigger: 'axis' },
  legend: { bottom: 0, textStyle: { fontSize: 11 } },
  grid: { top: 20, left: 40, right: 16, bottom: 36 },
  xAxis: {
    type: 'category',
    data: props.points.map((item) => item.date.slice(5)),
    axisLabel: { fontSize: 10 },
  },
  yAxis: {
    type: 'value',
    minInterval: 1,
    axisLabel: { fontSize: 10 },
  },
  series: [
    {
      name: '成功',
      type: 'bar',
      stack: 'requests',
      data: props.points.map((item) => item.success),
      itemStyle: { color: '#10b981', borderRadius: 0 },
    },
    {
      name: '失败',
      type: 'bar',
      stack: 'requests',
      data: props.points.map((item) => item.errors),
      itemStyle: { color: '#f43f5e', borderRadius: 0 },
    },
  ],
}))
</script>

<template>
  <AnalyticsChartCard
    title="每日请求量"
    description="先看稳定性，再看成本。成功/失败分开后，异常高峰会比单一总量更容易定位。"
    :loading="loading"
    :has-data="hasData"
  >
    <VChart :option="option" autoresize class="h-[260px]" />
  </AnalyticsChartCard>
</template>
