<script setup lang="ts">
// 文件说明：前端可复用界面组件。
import type { ScrollAreaScrollbarProps } from "reka-ui"
import type { HTMLAttributes } from "vue"
import { reactiveOmit } from "@vueuse/core"
import { ScrollAreaScrollbar, ScrollAreaThumb } from "reka-ui"
import { cn } from "@/lib/utils"

// 组件输入参数。
const props = withDefaults(defineProps<ScrollAreaScrollbarProps & { class?: HTMLAttributes["class"] }>(), {
  orientation: "vertical",
})

// 去除扩展字段后的透传参数。
const delegatedProps = reactiveOmit(props, "class")
</script>

<template>
  <ScrollAreaScrollbar
    v-bind="delegatedProps"
    :class="
      cn('flex touch-none select-none transition-colors',
         orientation === 'vertical'
           && 'h-full w-2.5 border-l border-l-transparent p-px',
         orientation === 'horizontal'
           && 'h-2.5 flex-col border-t border-t-transparent p-px',
         props.class)"
  >
    <ScrollAreaThumb class="relative flex-1 rounded-full bg-border" />
  </ScrollAreaScrollbar>
</template>
