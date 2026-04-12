<script setup lang="ts">
// 文件说明：前端可复用界面组件。
import { Layers3 } from 'lucide-vue-next'
import {
  Dialog,
  DialogDescription,
  DialogHeader,
  DialogScrollContent,
  DialogTitle,
} from '@/components/ui/dialog'
import ScriptDesignSimpleStructureEditor from '@/components/script-design/ScriptDesignSimpleStructureEditor.vue'
import type { ForeshadowRecord, ScriptDesign, ScriptEventNode, ScriptStage } from '@/domains/story/api/scriptDesignApi'

// 变量作用：变量 props，用于 props 相关配置或状态。
const props = defineProps<{
  open: boolean
  design: ScriptDesign | null
  saving?: boolean
}>()

// 变量作用：变量 emit，用于 emit 相关配置或状态。
const emit = defineEmits<{
  'update:open': [open: boolean]
  saveStructure: [payload: { stage_outlines: ScriptStage[]; event_nodes: ScriptEventNode[]; foreshadows: ForeshadowRecord[] }]
}>()
</script>

<template>
  <Dialog :open="open" @update:open="emit('update:open', $event)">
    <DialogScrollContent class="max-w-6xl p-0">
      <div class="border-b border-border bg-gradient-to-r from-stone-950 via-stone-900 to-amber-900/90 px-6 py-5 text-white">
        <DialogHeader>
          <DialogTitle class="flex items-center gap-2 text-xl font-semibold">
            <Layers3 class="h-5 w-5 text-amber-300" />
            主线结构设计器
          </DialogTitle>
          <DialogDescription class="text-stone-200">
            先完成阶段、关键事件与重要伏笔。每个区块内部都带有可展开的进阶设置，编辑位置与内容语义保持一致。
          </DialogDescription>
        </DialogHeader>
      </div>

      <div v-if="design" class="space-y-5 p-6">
        <div class="grid gap-3 md:grid-cols-3">
          <div class="rounded-2xl border border-stone-200 bg-stone-50 px-4 py-4">
            <p class="text-xs uppercase tracking-[0.16em] text-muted-foreground">阶段</p>
            <p class="mt-2 text-2xl font-semibold text-stone-900">{{ design.stage_outlines.length }}</p>
          </div>
          <div class="rounded-2xl border border-stone-200 bg-stone-50 px-4 py-4">
            <p class="text-xs uppercase tracking-[0.16em] text-muted-foreground">关键事件</p>
            <p class="mt-2 text-2xl font-semibold text-stone-900">{{ design.event_nodes.length }}</p>
          </div>
          <div class="rounded-2xl border border-stone-200 bg-stone-50 px-4 py-4">
            <p class="text-xs uppercase tracking-[0.16em] text-muted-foreground">伏笔</p>
            <p class="mt-2 text-2xl font-semibold text-stone-900">{{ design.foreshadows.length }}</p>
          </div>
        </div>

        <ScriptDesignSimpleStructureEditor
          :design="design"
          :saving="saving"
          @save="emit('saveStructure', $event)"
        />
      </div>
    </DialogScrollContent>
  </Dialog>
</template>