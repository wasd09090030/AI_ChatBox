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
  tooltip: { trigger: 'item', formatter: '{b}: {c} 次 ({d}%)' },
  legend: { bottom: 0, type: 'scroll', textStyle: { fontSize: 10 } },
  series: [
    {
      type: 'pie',
      radius: ['38%', '66%'],
      center: ['50%', '42%'],
      label: { fontSize: 10 },
      data: props.items.slice(0, 8).map((item, index) => ({
        name: item.label,
        value: item.value,
        itemStyle: {
          color: ['#2563eb', '#0ea5e9', '#14b8a6', '#84cc16', '#f97316', '#e11d48', '#7c3aed', '#64748b'][index % 8],
        },
      })),
    },
  ],
}))
</script>

<template>
  <AnalyticsChartCard
    title="模型使用分布"
    description="看清主力模型是否过于集中，避免少数模型把故事风格和成本一起锁死。"
    :loading="loading"
    :has-data="hasData"
    height-class="h-[220px]"
  >
    <VChart :option="option" autoresize class="h-[220px]" />
  </AnalyticsChartCard>
</template>
