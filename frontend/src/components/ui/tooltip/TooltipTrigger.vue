<script setup lang="ts">
// 文件说明：前端可复用界面组件。
import type { TooltipTriggerProps } from "reka-ui"
import { TooltipTrigger } from "reka-ui"

// 组件输入参数。
const props = defineProps<TooltipTriggerProps>()
</script>

<template>
  <TooltipTrigger v-bind="props">
    <slot />
  </TooltipTrigger>
</template>
