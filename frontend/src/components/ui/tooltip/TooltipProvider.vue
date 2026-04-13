<script setup lang="ts">
// 文件说明：前端可复用界面组件。
import type { TooltipProviderProps } from "reka-ui"
import { TooltipProvider } from "reka-ui"

// 组件输入参数。
const props = defineProps<TooltipProviderProps>()
</script>

<template>
  <TooltipProvider v-bind="props">
    <slot />
  </TooltipProvider>
</template>
