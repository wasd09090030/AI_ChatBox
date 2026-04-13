<script setup lang="ts">
// 文件说明：前端可复用界面组件。
import type { AlertDialogEmits, AlertDialogProps } from "reka-ui"
import { AlertDialogRoot, useForwardPropsEmits } from "reka-ui"

// 组件输入参数。
const props = defineProps<AlertDialogProps>()
// 组件事件声明。
const emits = defineEmits<AlertDialogEmits>()

// 透传到基础组件的参数与事件。
const forwarded = useForwardPropsEmits(props, emits)
</script>

<template>
  <AlertDialogRoot v-bind="forwarded">
    <slot />
  </AlertDialogRoot>
</template>
