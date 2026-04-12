<script setup lang="ts">
// 文件说明：前端可复用界面组件。
import type { HTMLAttributes } from "vue"
import { cn } from "@/lib/utils"

// 变量作用：变量 props，用于 props 相关配置或状态。
const props = defineProps<{
  class?: HTMLAttributes["class"]
}>()
</script>

<template>
  <span :class="cn('ml-auto text-xs tracking-widest opacity-60', props.class)">
    <slot />
  </span>
</template>
