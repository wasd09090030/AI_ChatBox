<script setup lang="ts">
// 文件说明：前端可复用界面组件。
import type { DialogCloseProps } from "reka-ui"
import { DialogClose } from "reka-ui"

// 组件输入参数。
const props = defineProps<DialogCloseProps>()
</script>

<template>
  <DialogClose v-bind="props">
    <slot />
  </DialogClose>
</template>
