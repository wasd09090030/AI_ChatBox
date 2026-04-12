<script setup lang="ts">
// 文件说明：前端可复用界面组件。
import { Globe, Plus, Pencil, Trash2, ChevronsLeft, ChevronsRight } from 'lucide-vue-next'
import { Button } from '@/components/ui/button'
import { ScrollArea } from '@/components/ui/scroll-area'
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
import { cn } from '@/lib/utils'
import { useSidebarCollapse } from '@/lib/useSidebarCollapse'

// 变量作用：变量 props，用于 props 相关配置或状态。
const props = defineProps<{
  worlds: World[] | undefined
  loading: boolean
  selectedId: string
}>()

// 变量作用：变量 emit，用于 emit 相关配置或状态。
const emit = defineEmits<{
  select: [id: string]
  add: []
  edit: [world: World]
  delete: [world: World]
}>()

// 变量作用：变量 collapsed，用于 collapsed 相关配置或状态。
const collapsed = useSidebarCollapse('world-sidebar-collapsed')
</script>

<template>
  <aside
    :class="
      cn(
        'flex shrink-0 flex-col overflow-hidden border-r border-border transition-[width] duration-200',
        collapsed ? 'w-14' : 'w-56',
      )
    "
  >
    <template v-if="collapsed">
      <div class="flex flex-1 flex-col items-center gap-2 px-2 py-3">
        <div class="flex h-10 w-10 items-center justify-center rounded-xl border border-border bg-muted/20">
          <Globe class="h-4 w-4 text-muted-foreground" />
        </div>
        <Button size="icon" variant="ghost" class="h-10 w-10 rounded-xl" title="新建世界" @click="emit('add')">
          <Plus class="h-4 w-4" />
        </Button>
      </div>
    </template>

    <template v-else>
      <div class="flex items-center justify-between px-3 py-3 border-b border-border">
        <p class="text-xs font-medium text-muted-foreground uppercase tracking-wide">世界</p>
        <Button size="icon" variant="ghost" class="h-6 w-6" @click="emit('add')">
          <Plus class="h-3.5 w-3.5" />
        </Button>
      </div>

      <ScrollArea class="flex-1">
        <div class="p-2 space-y-0.5">
          <div v-if="loading" class="px-2 py-4 text-center text-sm text-muted-foreground">
            加载中…
          </div>
          <div
            v-else-if="!worlds?.length"
            class="px-2 py-8 text-center text-sm text-muted-foreground"
          >
            <Globe class="h-8 w-8 mx-auto mb-2 opacity-30" />
            暂无世界
          </div>

          <div
            v-for="w in worlds"
            :key="w.id"
            :class="cn(
              'group flex items-center gap-2 px-2 py-2 rounded-md cursor-pointer text-sm transition-colors',
              selectedId === w.id
                ? 'bg-sidebar-accent text-sidebar-accent-foreground'
                : 'hover:bg-muted/60 text-foreground',
            )"
            @click="emit('select', w.id)"
          >
            <Globe class="h-3.5 w-3.5 shrink-0 text-muted-foreground" />
            <span class="flex-1 truncate">{{ w.name }}</span>

            <div class="opacity-0 group-hover:opacity-100 flex gap-0.5">
              <button class="p-0.5 hover:text-foreground" @click.stop="emit('edit', w)">
                <Pencil class="h-3 w-3 text-muted-foreground" />
              </button>
              <AlertDialog>
                <AlertDialogTrigger as-child>
                  <button class="p-0.5 hover:text-destructive" @click.stop>
                    <Trash2 class="h-3 w-3 text-muted-foreground" />
                  </button>
                </AlertDialogTrigger>
                <AlertDialogContent>
                  <AlertDialogHeader>
                    <AlertDialogTitle>删除世界</AlertDialogTitle>
                    <AlertDialogDescription>
                      确定要删除 "{{ w.name }}"？相关的 Lorebook 条目也会被删除。
                    </AlertDialogDescription>
                  </AlertDialogHeader>
                  <AlertDialogFooter>
                    <AlertDialogCancel>取消</AlertDialogCancel>
                    <AlertDialogAction variant="destructive" @click="emit('delete', w)">
                      删除
                    </AlertDialogAction>
                  </AlertDialogFooter>
                </AlertDialogContent>
              </AlertDialog>
            </div>
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
