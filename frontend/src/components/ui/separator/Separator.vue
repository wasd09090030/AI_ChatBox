<script setup lang="ts">
// 文件说明：前端可复用界面组件。
import type { SeparatorProps } from "reka-ui"
import type { HTMLAttributes } from "vue"
import { reactiveOmit } from "@vueuse/core"
import { Separator } from "reka-ui"
import { cn } from "@/lib/utils"

// 组件输入参数。
const props = withDefaults(defineProps<
  SeparatorProps & { class?: HTMLAttributes["class"] }
>(), {
  orientation: "horizontal",
  decorative: true,
})

// 去除扩展字段后的透传参数。
const delegatedProps = reactiveOmit(props, "class")
</script>

<template>
  <Separator
    v-bind="delegatedProps"
    :class="
      cn(
        'shrink-0 bg-border',
        props.orientation === 'horizontal' ? 'h-px w-full' : 'w-px h-full',
        props.class,
      )
    "
  />
</template>
