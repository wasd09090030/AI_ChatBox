<script setup lang="ts">
import { computed } from 'vue'
import { BookOpen, Plus, Trash2, Globe, FileText, ChevronsLeft, ChevronsRight } from 'lucide-vue-next'
import { Button } from '@/components/ui/button'
import { ScrollArea } from '@/components/ui/scroll-area'
import { cn } from '@/lib/utils'
import { useSidebarCollapse } from '@/lib/useSidebarCollapse'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from '@/components/ui/alert-dialog'
import type { World } from '@/services/lorebookService'
import type { StoredStory } from '@/components/story/types'

const props = withDefaults(
  defineProps<{
    selectedWorldId: string
    worlds?: World[]
    worldsLoading?: boolean
    stories?: StoredStory[]
    storiesLoading?: boolean
    currentStoryId?: string | null
  }>(),
  {
    worlds: () => [],
    worldsLoading: false,
    stories: () => [],
    storiesLoading: false,
    currentStoryId: null,
  },
)

const emit = defineEmits<{
  (event: 'update:selectedWorldId', value: string): void
  (event: 'create-story'): void
  (event: 'select-story', story: StoredStory): void
  (event: 'delete-story', story: StoredStory): void
}>()

const selectedWorldModel = computed({
  get: () => props.selectedWorldId,
  set: (value: string) => emit('update:selectedWorldId', value),
})

const collapsed = useSidebarCollapse('story-library-sidebar-collapsed')
</script>

<template>
  <aside
    :class="
      cn(
        'flex shrink-0 flex-col overflow-hidden border-r border-border transition-[width] duration-200',
        collapsed ? 'w-14' : 'w-60',
      )
    "
  >
    <template v-if="collapsed">
      <div class="flex flex-1 flex-col items-center gap-2 px-2 py-3">
        <div class="flex h-10 w-10 items-center justify-center rounded-xl border border-border bg-muted/20">
          <Globe class="h-4 w-4 text-muted-foreground" />
        </div>
        <div class="flex h-10 w-10 items-center justify-center rounded-xl border border-border bg-muted/20">
          <BookOpen class="h-4 w-4 text-muted-foreground" />
        </div>
        <Button
          size="icon"
          variant="ghost"
          class="h-10 w-10 rounded-xl"
          :disabled="!selectedWorldId"
          title="新建故事"
          @click="emit('create-story')"
        >
          <Plus class="h-4 w-4" />
        </Button>
      </div>
    </template>

    <template v-else>
      <div class="p-3 border-b border-border">
        <p class="text-xs font-medium text-muted-foreground mb-2 uppercase tracking-wide">世界</p>
        <Select v-model="selectedWorldModel">
          <SelectTrigger class="h-8 text-sm">
            <SelectValue placeholder="选择世界…" />
          </SelectTrigger>
          <SelectContent>
            <div v-if="worldsLoading" class="px-3 py-2 text-sm text-muted-foreground">加载中…</div>
            <template v-else-if="worlds.length">
              <SelectItem v-for="w in worlds" :key="w.id" :value="w.id">{{ w.name }}</SelectItem>
            </template>
            <div v-else class="px-3 py-2 text-sm text-muted-foreground">
              暂无世界，请先在 Lorebook 中创建
            </div>
          </SelectContent>
        </Select>
      </div>

      <div class="flex items-center justify-between px-3 py-2 border-b border-border">
        <p class="text-xs font-medium text-muted-foreground uppercase tracking-wide">故事</p>
        <Button
          size="icon"
          variant="ghost"
          class="h-6 w-6"
          :disabled="!selectedWorldId"
          @click="emit('create-story')"
        >
          <Plus class="h-3.5 w-3.5" />
        </Button>
      </div>

      <ScrollArea class="flex-1">
        <div class="p-2 space-y-0.5">
          <div v-if="storiesLoading" class="px-2 py-4 text-center text-sm text-muted-foreground">加载中…</div>
          <div v-else-if="!selectedWorldId" class="px-2 py-8 text-center text-sm text-muted-foreground">
            <Globe class="h-8 w-8 mx-auto mb-2 opacity-30" />
            请先选择世界
          </div>
          <div v-else-if="!stories.length" class="px-2 py-8 text-center text-sm text-muted-foreground">
            <FileText class="h-8 w-8 mx-auto mb-2 opacity-30" />
            暂无故事
          </div>
          <div
            v-for="story in stories"
            :key="story.id"
            :class="cn(
              'group flex items-center gap-2 px-2 py-2 rounded-md cursor-pointer text-sm transition-colors',
              currentStoryId === story.id
                ? 'bg-sidebar-accent text-sidebar-accent-foreground'
                : 'hover:bg-muted/60 text-foreground',
            )"
            @click="emit('select-story', story)"
          >
            <BookOpen class="h-3.5 w-3.5 shrink-0 text-muted-foreground" />
            <span class="flex-1 truncate">{{ story.title }}</span>
            <AlertDialog>
              <AlertDialogTrigger as-child>
                <Button
                  size="icon"
                  variant="ghost"
                  class="h-5 w-5 opacity-0 group-hover:opacity-100 shrink-0"
                  @click.stop
                >
                  <Trash2 class="h-3 w-3 text-muted-foreground" />
                </Button>
              </AlertDialogTrigger>
              <AlertDialogContent>
                <AlertDialogHeader>
                  <AlertDialogTitle>删除故事</AlertDialogTitle>
                  <AlertDialogDescription>
                    确定要删除 "{{ story.title }}"？此操作不可撤销。
                  </AlertDialogDescription>
                </AlertDialogHeader>
                <AlertDialogFooter>
                  <AlertDialogCancel>取消</AlertDialogCancel>
                  <AlertDialogAction variant="destructive" @click="emit('delete-story', story)">
                    删除
                  </AlertDialogAction>
                </AlertDialogFooter>
              </AlertDialogContent>
            </AlertDialog>
          </div>
        </div>
      </ScrollArea>
    </template>

    <div class="border-t border-border p-2 shrink-0">
      <Button
        variant="ghost"
        :title="collapsed ? '展开侧栏' : '收起侧栏'"
        :class="cn('h-9 w-full', collapsed ? 'px-0' : 'justify-start gap-2 px-2')"
        @click="collapsed = !collapsed"
      >
        <component :is="collapsed ? ChevronsRight : ChevronsLeft" class="h-4 w-4" />
        <span v-if="!collapsed">收起侧栏</span>
      </Button>
    </div>
  </aside>
</template>
