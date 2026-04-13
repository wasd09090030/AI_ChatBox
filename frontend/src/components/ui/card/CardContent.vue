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
  <div :class="cn('p-6 pt-0', props.class)">
    <slot />
  </div>
</template>
