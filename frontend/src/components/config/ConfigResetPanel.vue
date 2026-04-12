<script setup lang="ts">
// 文件说明：前端可复用界面组件。
import { RotateCcw } from 'lucide-vue-next'
import { Button } from '@/components/ui/button'
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

defineProps<{
  onReset: () => void | Promise<void>
}>()
</script>

<template>
  <section class="space-y-4">
    <div>
      <h2 class="text-base font-medium">重置</h2>
      <p class="mt-0.5 text-sm text-muted-foreground">将模型与生成参数恢复为默认值（API Key 不受影响）</p>
    </div>
    <AlertDialog>
      <AlertDialogTrigger as-child>
        <Button variant="outline" class="gap-2">
          <RotateCcw class="h-4 w-4" />
          恢复默认设置
        </Button>
      </AlertDialogTrigger>
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle>恢复默认设置</AlertDialogTitle>
          <AlertDialogDescription>
            将把提供商、模型、Temperature、Max Tokens 恢复为默认值。API Key 不受影响。
          </AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter>
          <AlertDialogCancel>取消</AlertDialogCancel>
          <AlertDialogAction @click="onReset">确认重置</AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  </section>
</template>
