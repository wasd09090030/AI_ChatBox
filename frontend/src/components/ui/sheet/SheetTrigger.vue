<script setup lang="ts">
// 文件说明：前端可复用界面组件。
import type { DialogTriggerProps } from "reka-ui"
import { DialogTrigger } from "reka-ui"

// 组件输入参数。
const props = defineProps<DialogTriggerProps>()
</script>

<template>
  <DialogTrigger v-bind="props">
    <slot />
  </DialogTrigger>
</template>
