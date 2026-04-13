<script setup lang="ts">
// 文件说明：前端可复用界面组件。
import type { SelectRootEmits, SelectRootProps } from "reka-ui"
import { SelectRoot, useForwardPropsEmits } from "reka-ui"

// 组件输入参数。
const props = defineProps<SelectRootProps>()
// 组件事件声明。
const emits = defineEmits<SelectRootEmits>()

// 透传到基础组件的参数与事件。
const forwarded = useForwardPropsEmits(props, emits)
</script>

<template>
  <SelectRoot v-bind="forwarded">
    <slot />
  </SelectRoot>
</template>
