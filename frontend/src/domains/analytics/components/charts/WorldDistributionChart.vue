<script setup lang="ts">
// 文件说明：前端业务域逻辑与接口封装。
import { computed } from 'vue'
import type { EChartsOption } from 'echarts'
import VChart from 'vue-echarts'
import '@/domains/analytics/lib/registerCharts'
import AnalyticsChartCard from '@/domains/analytics/components/AnalyticsChartCard.vue'
import type { AnalyticsDistributionItem } from '@/domains/analytics/types'

// 组件输入参数。
const props = defineProps<{
  items: AnalyticsDistributionItem[]
  loading?: boolean
}>()

// 布尔状态 hasData。
const hasData = computed(() => props.items.length > 0)

// option 相关状态。
const option = computed<EChartsOption>(() => {
  const topItems = props.items.slice(0, 8).reverse()
  return {
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
    grid: { top: 12, left: 92, right: 16, bottom: 20 },
    xAxis: {
      type: 'value',
      axisLabel: { fontSize: 10 },
    },
    yAxis: {
      type: 'category',
      data: topItems.map((item) => item.label),
      axisLabel: { fontSize: 10 },
    },
    series: [
      {
        type: 'bar',
        data: topItems.map((item) => item.value),
        itemStyle: { color: '#0f766e', borderRadius: 0 },
      },
    ],
  }
})
</script>

<template>
  <AnalyticsChartCard
    title="世界使用分布"
    description="如果某个世界占比过高，它就会主导创作路径；如果多个世界都低频，说明用户在探索阶段。"
    :loading="loading"
    :has-data="hasData"
    height-class="h-[260px]"
  >
    <VChart :option="option" autoresize class="h-[260px]" />
  </AnalyticsChartCard>
</template>
