<script setup lang="ts">
// 文件说明：前端可复用界面组件。
import type { TooltipProviderProps } from "reka-ui"
import { TooltipProvider } from "reka-ui"

// 变量作用：变量 props，用于 props 相关配置或状态。
const props = defineProps<TooltipProviderProps>()
</script>

<template>
  <TooltipProvider v-bind="props">
    <slot />
  </TooltipProvider>
</template>
