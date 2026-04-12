<script setup lang="ts">
// 文件说明：前端可复用界面组件。
import type { TooltipRootEmits, TooltipRootProps } from "reka-ui"
import { TooltipRoot, useForwardPropsEmits } from "reka-ui"

// 变量作用：变量 props，用于 props 相关配置或状态。
const props = defineProps<TooltipRootProps>()
// 变量作用：变量 emits，用于 emits 相关配置或状态。
const emits = defineEmits<TooltipRootEmits>()

// 变量作用：变量 forwarded，用于 forwarded 相关配置或状态。
const forwarded = useForwardPropsEmits(props, emits)
</script>

<template>
  <TooltipRoot v-bind="forwarded">
    <slot />
  </TooltipRoot>
</template>
