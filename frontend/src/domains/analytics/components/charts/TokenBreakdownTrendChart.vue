<script setup lang="ts">
// 文件说明：前端业务域逻辑与接口封装。
import { computed } from 'vue'
import type { EChartsOption } from 'echarts'
import VChart from 'vue-echarts'
import '@/domains/analytics/lib/registerCharts'
import AnalyticsChartCard from '@/domains/analytics/components/AnalyticsChartCard.vue'
import type { AnalyticsDailyStat } from '@/domains/analytics/types'

// 变量作用：变量 props，用于 props 相关配置或状态。
const props = defineProps<{
  points: AnalyticsDailyStat[]
  loading?: boolean
}>()

// 变量作用：变量 hasData，用于 hasData 相关配置或状态。
const hasData = computed(() => props.points.length > 0)

// 变量作用：变量 option，用于 option 相关配置或状态。
const option = computed<EChartsOption>(() => ({
  tooltip: {
    trigger: 'axis',
    valueFormatter: (value) => `${value} token`,
  },
  legend: { bottom: 0, textStyle: { fontSize: 11 } },
  grid: { top: 20, left: 52, right: 16, bottom: 36 },
  xAxis: {
    type: 'category',
    data: props.points.map((item) => item.date.slice(5)),
    axisLabel: { fontSize: 10 },
  },
  yAxis: {
    type: 'value',
    axisLabel: { fontSize: 10 },
  },
  series: [
    {
      name: 'Input',
      type: 'bar',
      stack: 'tokens',
      data: props.points.map((item) => item.input_tokens),
      itemStyle: { color: '#0ea5e9', borderRadius: 0 },
    },
    {
      name: 'Output',
      type: 'bar',
      stack: 'tokens',
      data: props.points.map((item) => item.output_tokens),
      itemStyle: { color: '#f59e0b', borderRadius: 0 },
    },
    {
      name: 'Total',
      type: 'line',
      smooth: true,
      data: props.points.map((item) => item.tokens),
      symbolSize: 7,
      itemStyle: { color: '#111827' },
      lineStyle: { color: '#111827', width: 2 },
    },
  ],
}))
</script>

<template>
  <AnalyticsChartCard
    title="Token 消耗拆分"
    description="把 input、output 和 total 分开看，才能判断是上下文膨胀，还是生成本身过长。"
    :loading="loading"
    :has-data="hasData"
  >
    <VChart :option="option" autoresize class="h-[260px]" />
  </AnalyticsChartCard>
</template>
