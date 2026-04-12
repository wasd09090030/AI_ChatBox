<script setup lang="ts">
// 文件说明：前端业务域逻辑与接口封装。
import { computed } from 'vue'
import type { EChartsOption } from 'echarts'
import VChart from 'vue-echarts'
import '@/domains/analytics/lib/registerCharts'
import AnalyticsChartCard from '@/domains/analytics/components/AnalyticsChartCard.vue'
import type { AnalyticsDistributionItem } from '@/domains/analytics/types'

// 变量作用：变量 props，用于 props 相关配置或状态。
const props = defineProps<{
  items: AnalyticsDistributionItem[]
  loading?: boolean
}>()

// 变量作用：变量 hasData，用于 hasData 相关配置或状态。
const hasData = computed(() => props.items.length > 0)

// 变量作用：变量 option，用于 option 相关配置或状态。
const option = computed<EChartsOption>(() => ({
  tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
  grid: { top: 16, left: 40, right: 16, bottom: 52 },
  xAxis: {
    type: 'category',
    data: props.items.map((item) => item.label),
    axisLabel: { fontSize: 10, rotate: 20 },
  },
  yAxis: {
    type: 'value',
    minInterval: 1,
    axisLabel: { fontSize: 10 },
  },
  series: [
    {
      type: 'bar',
      data: props.items.map((item) => item.value),
      itemStyle: { color: '#7c3aed', borderRadius: 0 },
    },
  ],
}))
</script>

<template>
  <AnalyticsChartCard
    title="请求类型分布"
    description="帮助区分是故事生成、回滚还是其他请求类型在拉高系统压力。"
    :loading="loading"
    :has-data="hasData"
    height-class="h-[260px]"
  >
    <VChart :option="option" autoresize class="h-[260px]" />
  </AnalyticsChartCard>
</template>
