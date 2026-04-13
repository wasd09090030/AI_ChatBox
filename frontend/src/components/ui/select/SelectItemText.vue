<script setup lang="ts">
// 文件说明：前端可复用界面组件。
import type { SelectItemTextProps } from "reka-ui"
import { SelectItemText } from "reka-ui"

// 组件输入参数。
const props = defineProps<SelectItemTextProps>()
</script>

<template>
  <SelectItemText v-bind="props">
    <slot />
  </SelectItemText>
</template>
