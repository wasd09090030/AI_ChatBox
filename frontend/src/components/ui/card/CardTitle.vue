<script setup lang="ts">
// 文件说明：前端可复用界面组件。
import type { HTMLAttributes } from "vue"
import { cn } from "@/lib/utils"

// 组件输入参数。
const props = defineProps<{
  class?: HTMLAttributes["class"]
}>()
</script>

<template>
  <h3
    :class="
      cn('font-semibold leading-none tracking-tight', props.class)
    "
  >
    <slot />
  </h3>
</template>
