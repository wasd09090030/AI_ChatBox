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
    valueFormatter: (value) => `${Number(value).toFixed(2)}s`,
  },
  grid: { top: 20, left: 48, right: 16, bottom: 28 },
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
      type: 'line',
      smooth: true,
      data: props.points.map((item) => item.avg_generation_time),
      areaStyle: { color: 'rgba(249,115,22,0.15)' },
      lineStyle: { color: '#f97316', width: 2 },
      itemStyle: { color: '#f97316' },
      symbolSize: 7,
    },
  ],
}))
</script>

<template>
  <AnalyticsChartCard
    title="生成耗时趋势"
    description="如果耗时升高但 output 没增加，说明模型或上下文链路正在吞性能。"
    :loading="loading"
    :has-data="hasData"
    height-class="h-[220px]"
  >
    <VChart :option="option" autoresize class="h-[220px]" />
  </AnalyticsChartCard>
</template>
