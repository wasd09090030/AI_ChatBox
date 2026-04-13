<script setup lang="ts">
// 文件说明：前端可复用界面组件。
import type { SelectLabelProps } from "reka-ui"
import type { HTMLAttributes } from "vue"
import { SelectLabel } from "reka-ui"
import { cn } from "@/lib/utils"

// 组件输入参数。
const props = defineProps<SelectLabelProps & { class?: HTMLAttributes["class"] }>()
</script>

<template>
  <SelectLabel :class="cn('px-2 py-1.5 text-sm font-semibold', props.class)">
    <slot />
  </SelectLabel>
</template>
