<script setup lang="ts">
// 文件说明：前端可复用界面组件。
import type { HTMLAttributes } from "vue"
import type { BadgeVariants } from "."
import { cn } from "@/lib/utils"
import { badgeVariants } from "."

// 组件输入参数。
const props = defineProps<{
  variant?: BadgeVariants["variant"]
  class?: HTMLAttributes["class"]
}>()
</script>

<template>
  <div :class="cn(badgeVariants({ variant }), props.class)">
    <slot />
  </div>
</template>
