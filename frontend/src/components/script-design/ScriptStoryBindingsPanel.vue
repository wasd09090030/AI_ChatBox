<script setup lang="ts">
import { Link2 } from 'lucide-vue-next'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import type { StoryBindingSummary } from '@/domains/story/api/scriptDesignApi'

defineProps<{
  items: StoryBindingSummary[]
  loading?: boolean
}>()
</script>

<template>
  <Card>
    <CardHeader>
      <CardTitle>关联故事</CardTitle>
      <CardDescription>首版只读展示哪些故事已经引用该剧本设计。</CardDescription>
    </CardHeader>
    <CardContent>
      <div v-if="loading" class="text-sm text-muted-foreground">加载中…</div>
      <div v-else-if="!items.length" class="rounded-lg border border-dashed border-border px-4 py-6 text-sm text-muted-foreground text-center">
        暂无关联故事
      </div>
      <div v-else class="space-y-2">
        <div v-for="item in items" :key="item.story_id" class="rounded-lg border border-border p-3">
          <div class="flex items-center justify-between gap-2">
            <div class="min-w-0">
              <div class="flex items-center gap-2">
                <Link2 class="h-4 w-4 text-muted-foreground shrink-0" />
                <p class="text-sm font-medium truncate">{{ item.title }}</p>
              </div>
              <p class="mt-1 text-xs text-muted-foreground">{{ item.world_name }}</p>
            </div>
            <Badge variant="secondary">{{ item.updated_at.slice(0, 10) }}</Badge>
          </div>
        </div>
      </div>
    </CardContent>
  </Card>
</template>