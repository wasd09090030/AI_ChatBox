<script setup lang="ts">
// 文件说明：前端可复用界面组件。
import type { AlertDialogTriggerProps } from "reka-ui"
import { AlertDialogTrigger } from "reka-ui"

// 组件输入参数。
const props = defineProps<AlertDialogTriggerProps>()
</script>

<template>
  <AlertDialogTrigger v-bind="props">
    <slot />
  </AlertDialogTrigger>
</template>
