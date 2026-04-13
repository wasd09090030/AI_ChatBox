<script setup lang="ts">
// 文件说明：前端可复用界面组件。
import type { DropdownMenuSubEmits, DropdownMenuSubProps } from "reka-ui"
import {
  DropdownMenuSub,
  useForwardPropsEmits,
} from "reka-ui"

// 组件输入参数。
const props = defineProps<DropdownMenuSubProps>()
// 组件事件声明。
const emits = defineEmits<DropdownMenuSubEmits>()

// 透传到基础组件的参数与事件。
const forwarded = useForwardPropsEmits(props, emits)
</script>

<template>
  <DropdownMenuSub v-bind="forwarded">
    <slot />
  </DropdownMenuSub>
</template>
