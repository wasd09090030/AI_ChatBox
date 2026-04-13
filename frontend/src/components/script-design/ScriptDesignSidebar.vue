<script setup lang="ts">
// 文件说明：前端可复用界面组件。
import { BookOpenText, Plus, Trash2, ChevronsLeft, ChevronsRight } from 'lucide-vue-next'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { ScrollArea } from '@/components/ui/scroll-area'
import type { ScriptDesign, ScriptDesignSidebarWorld } from '@/domains/story/api/scriptDesignApi'
import { cn } from '@/lib/utils'
import { useSidebarCollapse } from '@/lib/useSidebarCollapse'

defineProps<{
  worlds: ScriptDesignSidebarWorld[]
  worldsLoading: boolean
  selectedWorldId: string
  scriptDesigns: ScriptDesign[]
  scriptDesignsLoading: boolean
  selectedScriptDesignId: string
  creatingDisabled?: boolean
}>()

// 组件事件派发器。
const emit = defineEmits<{
  'select-world': [worldId: string]
  'select-script': [scriptDesignId: string]
  'create-script': []
  'delete-script': [scriptDesign: ScriptDesign]
}>()

// collapsed 相关状态。
const collapsed = useSidebarCollapse('script-design-sidebar-collapsed')
</script>

<template>
  <aside
    :class="
      cn(
        'flex shrink-0 flex-col overflow-hidden border-r border-border bg-muted/10 transition-[width] duration-200',
        collapsed ? 'w-14' : 'w-80',
      )
    "
  >
    <template v-if="collapsed">
      <div class="flex flex-1 flex-col items-center gap-2 px-2 py-3">
        <div class="flex h-10 w-10 items-center justify-center rounded-xl border border-border bg-background/80">
          <BookOpenText class="h-4 w-4 text-muted-foreground" />
        </div>
        <Button
          size="icon"
          variant="ghost"
          class="h-10 w-10 rounded-xl"
          :disabled="creatingDisabled || !selectedWorldId"
          title="新建剧本设计"
          @click="emit('create-script')"
        >
          <Plus class="h-4 w-4" />
        </Button>
      </div>
    </template>

    <template v-else>
      <div class="p-4 border-b border-border space-y-3">
        <div>
          <p class="text-sm font-medium">剧本设计</p>
          <p class="text-xs text-muted-foreground mt-1">按世界维护主线阶段、关键事件与伏笔记录。</p>
        </div>

        <div class="space-y-1.5">
          <label class="text-xs font-medium text-muted-foreground">所属世界</label>
          <select
            :value="selectedWorldId"
            class="flex h-9 w-full rounded-md border border-input bg-background px-3 py-1 text-sm shadow-sm"
            @change="emit('select-world', ($event.target as HTMLSelectElement).value)"
          >
            <option value="">请选择世界</option>
            <option v-for="world in worlds" :key="world.id" :value="world.id">
              {{ world.name }}
            </option>
          </select>
        </div>

        <Button class="w-full gap-1.5" :disabled="creatingDisabled || !selectedWorldId" @click="emit('create-script')">
          <Plus class="h-4 w-4" />新建剧本设计
        </Button>
      </div>

      <ScrollArea class="flex-1">
        <div class="p-3 space-y-2">
          <div v-if="worldsLoading || scriptDesignsLoading" class="text-sm text-muted-foreground py-6 text-center">
            加载中…
          </div>
          <div v-else-if="!selectedWorldId" class="text-sm text-muted-foreground py-6 text-center">
            请选择一个世界
          </div>
          <div v-else-if="!scriptDesigns.length" class="text-sm text-muted-foreground py-6 text-center">
            当前世界还没有剧本设计
          </div>

          <button
            v-for="design in scriptDesigns"
            :key="design.id"
            class="w-full rounded-xl border text-left p-3 transition-colors"
            :class="design.id === selectedScriptDesignId ? 'border-primary bg-primary/5' : 'border-border bg-background hover:bg-muted/50'"
            @click="emit('select-script', design.id)"
          >
            <div class="flex items-start justify-between gap-2">
              <div class="min-w-0">
                <div class="flex items-center gap-2">
                  <BookOpenText class="h-4 w-4 text-muted-foreground shrink-0" />
                  <p class="text-sm font-medium truncate">{{ design.title }}</p>
                </div>
                <p class="mt-1 text-xs text-muted-foreground line-clamp-2">
                  {{ design.logline || design.summary || '暂无概要' }}
                </p>
              </div>
              <button
                class="rounded-md p-1 text-muted-foreground hover:bg-destructive/10 hover:text-destructive"
                type="button"
                @click.stop="emit('delete-script', design)"
              >
                <Trash2 class="h-4 w-4" />
              </button>
            </div>

            <div class="mt-3 flex items-center justify-between">
              <Badge variant="secondary" class="text-[11px]">{{ design.status }}</Badge>
              <span class="text-[11px] text-muted-foreground">
                {{ design.stage_outlines.length }} 阶段 / {{ design.event_nodes.length }} 事件
              </span>
            </div>
          </button>
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
