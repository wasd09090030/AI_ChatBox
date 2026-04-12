<script setup lang="ts">
// 文件说明：前端可复用界面组件。
import { computed } from 'vue'
import { Layers3, Milestone, FlagTriangleRight, WandSparkles } from 'lucide-vue-next'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import type { ScriptDesign } from '@/domains/story/api/scriptDesignApi'

// 变量作用：变量 props，用于 props 相关配置或状态。
const props = defineProps<{
  design: ScriptDesign
}>()

// 变量作用：变量 emit，用于 emit 相关配置或状态。
const emit = defineEmits<{
  openDesigner: []
}>()

// 变量作用：变量 orderedStages，用于 orderedStages 相关配置或状态。
const orderedStages = computed(() => props.design.stage_outlines.slice().sort((a, b) => a.order - b.order))
// 变量作用：变量 stagePreview，用于 stagePreview 相关配置或状态。
const stagePreview = computed(() => orderedStages.value.slice(0, 4))
</script>

<template>
  <Card class="border-stone-200 bg-gradient-to-br from-stone-50 via-white to-amber-50/40 shadow-sm">
    <CardHeader>
      <CardTitle class="flex items-center gap-2 text-stone-900">
        <Layers3 class="h-4 w-4 text-amber-700" />
        主线结构
      </CardTitle>
      <CardDescription>首页只看骨架摘要，点击后进入独立结构设计器，避免单页堆满阶段、事件和伏笔编辑内容。</CardDescription>
    </CardHeader>
    <CardContent class="space-y-4">
      <div class="grid gap-3 sm:grid-cols-3">
        <div class="rounded-xl border border-stone-200 bg-white/90 px-3 py-3">
          <p class="text-xs uppercase tracking-[0.16em] text-muted-foreground">阶段</p>
          <p class="mt-2 text-2xl font-semibold text-stone-900">{{ design.stage_outlines.length }}</p>
        </div>
        <div class="rounded-xl border border-stone-200 bg-white/90 px-3 py-3">
          <p class="text-xs uppercase tracking-[0.16em] text-muted-foreground">关键事件</p>
          <p class="mt-2 text-2xl font-semibold text-stone-900">{{ design.event_nodes.length }}</p>
        </div>
        <div class="rounded-xl border border-stone-200 bg-white/90 px-3 py-3">
          <p class="text-xs uppercase tracking-[0.16em] text-muted-foreground">伏笔</p>
          <p class="mt-2 text-2xl font-semibold text-stone-900">{{ design.foreshadows.length }}</p>
        </div>
      </div>

      <div class="rounded-2xl border border-stone-200 bg-white/85 p-4">
        <div class="flex items-center justify-between gap-3">
          <div>
            <p class="text-sm font-semibold text-stone-900">当前阶段预览</p>
            <p class="mt-1 text-xs text-muted-foreground">建议先完成 3 到 5 个主要阶段，再逐步充实事件与伏笔。</p>
          </div>
          <Milestone class="h-4 w-4 text-amber-700" />
        </div>

        <div v-if="!stagePreview.length" class="mt-4 rounded-xl border border-dashed border-stone-200 px-4 py-6 text-center text-sm text-muted-foreground">
          还没有主线阶段，先进入结构设计器建立故事骨架。
        </div>
        <div v-else class="mt-4 space-y-2">
          <div v-for="(stage, index) in stagePreview" :key="stage.id" class="flex items-start gap-3 rounded-xl border border-stone-200 px-3 py-3">
            <div class="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-stone-900 text-xs font-semibold text-white">
              {{ index + 1 }}
            </div>
            <div class="min-w-0">
              <p class="text-sm font-medium text-stone-900 truncate">{{ stage.title }}</p>
              <p class="mt-1 text-xs text-muted-foreground line-clamp-2">{{ stage.goal || stage.expected_turning_point || '待补充阶段说明' }}</p>
            </div>
          </div>
        </div>
      </div>

      <div class="rounded-2xl border border-dashed border-amber-300 bg-amber-50/70 px-4 py-3">
        <div class="flex items-start gap-3">
          <FlagTriangleRight class="mt-0.5 h-4 w-4 shrink-0 text-amber-700" />
          <div>
            <p class="text-sm font-medium text-stone-900">结构设计器包含进阶项</p>
            <p class="mt-1 text-xs text-stone-600">阶段增强、事件增强和伏笔增强都在同一个模态框里按需展开，不会再出现“在这里勾选、在别处编辑”的跳跃感。</p>
          </div>
        </div>
      </div>

      <div class="flex justify-end">
        <Button class="gap-1.5" @click="emit('openDesigner')">
          <WandSparkles class="h-4 w-4" />打开结构设计器
        </Button>
      </div>
    </CardContent>
  </Card>
</template>