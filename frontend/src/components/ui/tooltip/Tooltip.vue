<script setup lang="ts">
// 文件说明：前端可复用界面组件。
import type { TooltipRootEmits, TooltipRootProps } from "reka-ui"
import { TooltipRoot, useForwardPropsEmits } from "reka-ui"

// 组件输入参数。
const props = defineProps<TooltipRootProps>()
// 组件事件声明。
const emits = defineEmits<TooltipRootEmits>()

// 透传到基础组件的参数与事件。
const forwarded = useForwardPropsEmits(props, emits)
</script>

<template>
  <TooltipRoot v-bind="forwarded">
    <slot />
  </TooltipRoot>
</template>
