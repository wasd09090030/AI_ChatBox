<script setup lang="ts">
// 文件说明：前端业务域逻辑与接口封装。
import { Brain, History } from 'lucide-vue-next'
import { Badge } from '@/components/ui/badge'
import { useStorySessionStore } from '@/stores/storySession'

// 变量作用：变量 storySessionStore，用于 storySessionStore 相关配置或状态。
const storySessionStore = useStorySessionStore()
</script>

<template>
  <section class="overflow-hidden rounded-2xl border border-border bg-card/80 shadow-sm shadow-black/5">
    <div class="flex items-center justify-between border-b border-border bg-muted/20 px-4 py-3">
      <div class="flex items-center gap-2">
        <Brain class="h-3.5 w-3.5 text-violet-500" />
        <h3 class="text-sm font-semibold">故事摘要记忆</h3>
      </div>
      <div class="flex items-center gap-2">
        <Badge variant="secondary" class="text-[10px]">{{ storySessionStore.getAllSummaries().length }} 条摘要</Badge>
        <Badge variant="outline" class="text-[10px]">{{ storySessionStore.getRecentMemoryEvents().length }} 条事件</Badge>
      </div>
    </div>

    <div v-if="storySessionStore.getAllSummaries().length === 0" class="px-4 py-10 text-center text-sm text-muted-foreground">
      暂无摘要记忆，请先在故事页进行创作。
    </div>
    <div v-else class="divide-y divide-border">
      <article
        v-for="record in storySessionStore.getAllSummaries()"
        :key="record.sessionId"
        class="px-4 py-3 transition-colors hover:bg-muted/20"
      >
        <div class="mb-2 flex items-start justify-between gap-3">
          <p class="truncate text-sm font-medium">{{ record.storyTitle }}</p>
          <div class="flex shrink-0 items-center gap-2">
            <Badge variant="outline" class="text-[10px] font-mono">Turn {{ record.last_turn }}</Badge>
            <span class="text-[10px] text-muted-foreground">{{ record.updatedAt.slice(0, 16).replace('T', ' ') }}</span>
          </div>
        </div>
        <p class="text-xs leading-6 text-muted-foreground">{{ record.summary_text }}</p>
        <div v-if="record.key_facts?.length" class="mt-2 flex flex-wrap gap-1.5">
          <Badge
            v-for="fact in record.key_facts.slice(0, 4)"
            :key="fact"
            variant="secondary"
            class="text-[10px] font-normal"
          >
            {{ fact }}
          </Badge>
          <Badge v-if="record.key_facts.length > 4" variant="secondary" class="text-[10px] font-normal">
            +{{ record.key_facts.length - 4 }} 更多
          </Badge>
        </div>
      </article>
    </div>

    <div class="border-t border-border bg-muted/10 px-4 py-3">
      <div class="mb-3 flex items-center gap-2">
        <History class="h-3.5 w-3.5 text-sky-600" />
        <h4 class="text-xs font-semibold uppercase tracking-wide text-muted-foreground">最近记忆事件</h4>
      </div>
      <div v-if="storySessionStore.getRecentMemoryEvents(6).length" class="space-y-2">
        <div
          v-for="event in storySessionStore.getRecentMemoryEvents(6)"
          :key="event.eventId"
          class="rounded-xl border border-border/70 bg-background/80 px-3 py-2"
        >
          <div class="flex items-center justify-between gap-2">
            <p class="truncate text-xs font-medium">{{ event.storyTitle || event.sessionId }}</p>
            <Badge variant="outline" class="text-[10px] font-mono">{{ event.memoryLayer }}/{{ event.action }}</Badge>
          </div>
          <p class="mt-1 text-[11px] text-muted-foreground">{{ event.title }}</p>
          <p v-if="event.reason" class="mt-1 text-[10px] text-muted-foreground">{{ event.reason }}</p>
        </div>
      </div>
      <p v-else class="text-xs text-muted-foreground">暂无结构化记忆事件。</p>
    </div>
  </section>
</template>
