<script setup lang="ts">
// 文件说明：前端可复用界面组件。
import type { DropdownMenuRadioGroupEmits, DropdownMenuRadioGroupProps } from "reka-ui"
import {
  DropdownMenuRadioGroup,
  useForwardPropsEmits,
} from "reka-ui"

// 组件输入参数。
const props = defineProps<DropdownMenuRadioGroupProps>()
// 组件事件声明。
const emits = defineEmits<DropdownMenuRadioGroupEmits>()

// 透传到基础组件的参数与事件。
const forwarded = useForwardPropsEmits(props, emits)
</script>

<template>
  <DropdownMenuRadioGroup v-bind="forwarded">
    <slot />
  </DropdownMenuRadioGroup>
</template>
