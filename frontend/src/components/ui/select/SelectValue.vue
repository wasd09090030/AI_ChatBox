<script setup lang="ts">
// 文件说明：前端可复用界面组件。
import type { SelectValueProps } from "reka-ui"
import { SelectValue } from "reka-ui"

// 组件输入参数。
const props = defineProps<SelectValueProps>()
</script>

<template>
  <SelectValue v-bind="props">
    <slot />
  </SelectValue>
</template>
