<script setup lang="ts">
// 文件说明：前端可复用界面组件。
import { Plus, Pencil, Trash2, UserRound } from 'lucide-vue-next'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
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
import type { PersonaProfile } from '@/services/roleplayService'

defineProps<{
  personas?: PersonaProfile[]
  personasLoading: boolean
}>()

// 变量作用：变量 emit，用于 emit 相关配置或状态。
const emit = defineEmits<{
  (event: 'new-persona'): void
  (event: 'edit-persona', persona: PersonaProfile): void
  (event: 'delete-persona', persona: PersonaProfile): void
}>()
</script>

<template>
  <div class="space-y-4">
    <div class="flex items-center justify-between">
      <p class="text-sm text-muted-foreground">
        {{ personas?.length ?? 0 }} 个人设
      </p>
      <Button size="sm" class="gap-1.5" @click="emit('new-persona')">
        <Plus class="h-4 w-4" />
        新建人设
      </Button>
    </div>

    <div v-if="personasLoading" class="py-12 text-center text-sm text-muted-foreground">
      加载中…
    </div>
    <div
      v-else-if="!personas?.length"
      class="py-16 text-center text-muted-foreground border border-dashed border-border rounded-xl"
    >
      <UserRound class="h-12 w-12 mx-auto mb-3 opacity-20" />
      <p class="text-sm font-medium">暂无人设</p>
      <p class="text-xs mt-1 opacity-70">点击「新建人设」开始创建</p>
    </div>

    <div v-else class="grid grid-cols-1 sm:grid-cols-2 gap-4">
      <div
        v-for="p in personas"
        :key="p.id"
        class="border border-border rounded-xl p-4 space-y-3 hover:bg-muted/30 transition-colors"
      >
        <div class="flex items-start justify-between gap-2">
          <div class="min-w-0">
            <p class="font-medium text-sm truncate">{{ p.name }}</p>
            <p v-if="p.title" class="text-xs text-muted-foreground">{{ p.title }}</p>
            <p class="text-xs text-muted-foreground mt-0.5 line-clamp-2">
              {{ p.description || '（无描述）' }}
            </p>
          </div>
          <div class="flex gap-1 shrink-0">
            <Button size="icon" variant="ghost" class="h-7 w-7" @click="emit('edit-persona', p)">
              <Pencil class="h-3.5 w-3.5" />
            </Button>
            <AlertDialog>
              <AlertDialogTrigger as-child>
                <Button size="icon" variant="ghost" class="h-7 w-7 text-destructive hover:text-destructive">
                  <Trash2 class="h-3.5 w-3.5" />
                </Button>
              </AlertDialogTrigger>
              <AlertDialogContent>
                <AlertDialogHeader>
                  <AlertDialogTitle>删除人设</AlertDialogTitle>
                  <AlertDialogDescription>
                    确定要删除 "{{ p.name }}"？此操作不可撤销。
                  </AlertDialogDescription>
                </AlertDialogHeader>
                <AlertDialogFooter>
                  <AlertDialogCancel>取消</AlertDialogCancel>
                  <AlertDialogAction variant="destructive" @click="emit('delete-persona', p)">
                    删除
                  </AlertDialogAction>
                </AlertDialogFooter>
              </AlertDialogContent>
            </AlertDialog>
          </div>
        </div>
        <div v-if="p.traits?.length" class="flex flex-wrap gap-1">
          <Badge
            v-for="trait in p.traits"
            :key="trait"
            variant="outline"
            class="text-[11px] px-1.5 py-0"
          >
            {{ trait }}
          </Badge>
        </div>
      </div>
    </div>
  </div>
</template>
