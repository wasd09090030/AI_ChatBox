<script setup lang="ts">
// 文件说明：前端业务域逻辑与接口封装。
import { computed } from 'vue'
import { BrainCircuit, Compass, Orbit } from 'lucide-vue-next'
import { Badge } from '@/components/ui/badge'
import type { AnalyticsOverview } from '@/domains/analytics/types'
import { formatPercent } from '@/domains/analytics/utils/formatters'

// 变量作用：变量 props，用于 props 相关配置或状态。
const props = defineProps<{
  overview: AnalyticsOverview | undefined
  topModelLabel: string
  topWorldLabel: string
}>()

// 变量作用：变量 tokenDirectionHint，用于 tokenDirectionHint 相关配置或状态。
const tokenDirectionHint = computed(() => {
  if (!props.overview) return 'Token 结构会告诉你问题更像是上下文膨胀，还是生成阶段失控。'
  const { avg_input_tokens, avg_output_tokens } = props.overview
  if (avg_input_tokens > avg_output_tokens * 3) {
    return '输入 token 明显高于输出，说明上下文和设定注入较重，适合先压缩摘要、减少一次性设定投喂。'
  }
  if (avg_output_tokens > avg_input_tokens * 1.4) {
    return '输出 token 偏高，模型正在持续扩写。若故事开始失控，优先收紧 focus、作者注记和 max tokens。'
  }
  return '输入输出比例比较均衡，当前更应关注模型选择和上下文命中质量，而不是盲目压长度。'
})

// 变量作用：变量 retrievalHint，用于 retrievalHint 相关配置或状态。
const retrievalHint = computed(() => {
  if (!props.overview) return '检索命中会影响故事是否稳定贴合世界设定。'
  if (props.overview.avg_retrieved_context_count >= 4) {
    return '平均上下文命中较高，说明故事正在强绑定设定。若文风僵硬，可以降低显式注入或整理 lorebook 粒度。'
  }
  if (props.overview.avg_retrieved_context_count <= 1) {
    return '上下文命中偏低，角色与地点信息可能没有稳定注入。可以补关键词、提升条目命中概率，避免剧情漂移。'
  }
  return '上下文命中处于中位区间，适合继续用事件表定位到底是哪个模型或世界在拉高波动。'
})

// 变量作用：变量 coverageHint，用于 coverageHint 相关配置或状态。
const coverageHint = computed(() => {
  if (!props.overview) return 'Provider usage 覆盖率越高，token 统计越接近真实成本。'
  return `当前 provider usage 覆盖率 ${formatPercent(props.overview.provider_usage_rate)}，主力模型是 ${props.topModelLabel}，主力世界是 ${props.topWorldLabel}。`
})
</script>

<template>
  <section class="grid gap-3 xl:grid-cols-3">
    <article class="rounded-2xl border border-border bg-gradient-to-br from-sky-500/10 via-background to-background p-4 shadow-sm shadow-black/5">
      <div class="mb-3 flex items-center gap-2 text-sm font-semibold text-foreground">
        <BrainCircuit class="h-4 w-4 text-sky-500" />
        Token 走向提示
      </div>
      <p class="text-sm leading-6 text-muted-foreground">{{ tokenDirectionHint }}</p>
    </article>

    <article class="rounded-2xl border border-border bg-gradient-to-br from-emerald-500/10 via-background to-background p-4 shadow-sm shadow-black/5">
      <div class="mb-3 flex items-center gap-2 text-sm font-semibold text-foreground">
        <Compass class="h-4 w-4 text-emerald-500" />
        设定命中提示
      </div>
      <p class="text-sm leading-6 text-muted-foreground">{{ retrievalHint }}</p>
    </article>

    <article class="rounded-2xl border border-border bg-gradient-to-br from-amber-500/10 via-background to-background p-4 shadow-sm shadow-black/5">
      <div class="mb-3 flex items-center gap-2 text-sm font-semibold text-foreground">
        <Orbit class="h-4 w-4 text-amber-500" />
        分布观察
      </div>
      <p class="mb-3 text-sm leading-6 text-muted-foreground">{{ coverageHint }}</p>
      <div class="flex flex-wrap gap-2">
        <Badge variant="outline">活跃会话 {{ props.overview?.active_sessions ?? 0 }}</Badge>
        <Badge variant="outline">活跃世界 {{ props.overview?.active_worlds ?? 0 }}</Badge>
      </div>
    </article>
  </section>
</template>