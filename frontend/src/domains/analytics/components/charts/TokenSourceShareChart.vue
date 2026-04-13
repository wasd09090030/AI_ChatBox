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
const option = computed<EChartsOption>(() => ({
  tooltip: { trigger: 'item', formatter: '{b}: {c} ({d}%)' },
  legend: { bottom: 0, textStyle: { fontSize: 10 } },
  series: [
    {
      type: 'pie',
      radius: ['42%', '68%'],
      center: ['50%', '42%'],
      label: { fontSize: 10 },
      itemStyle: {
        borderColor: 'rgba(255,255,255,0.85)',
        borderWidth: 2,
      },
      data: props.items.map((item, index) => ({
        name: item.label,
        value: item.value,
        itemStyle: {
          color: index === 0 ? '#111827' : '#94a3b8',
        },
      })),
    },
  ],
}))
</script>

<template>
  <AnalyticsChartCard
    title="Token 统计来源"
    description="真实 provider usage 越多，成本统计越可信；估算越多，越应该谨慎看待 total token。"
    :loading="loading"
    :has-data="hasData"
    height-class="h-[220px]"
  >
    <VChart :option="option" autoresize class="h-[220px]" />
  </AnalyticsChartCard>
</template>
