<script setup lang="ts">
// 文件说明：前端可复用界面组件。
import type { DropdownMenuRootEmits, DropdownMenuRootProps } from "reka-ui"
import { DropdownMenuRoot, useForwardPropsEmits } from "reka-ui"

// 组件输入参数。
const props = defineProps<DropdownMenuRootProps>()
// 组件事件声明。
const emits = defineEmits<DropdownMenuRootEmits>()

// 透传到基础组件的参数与事件。
const forwarded = useForwardPropsEmits(props, emits)
</script>

<template>
  <DropdownMenuRoot v-bind="forwarded">
    <slot />
  </DropdownMenuRoot>
</template>
