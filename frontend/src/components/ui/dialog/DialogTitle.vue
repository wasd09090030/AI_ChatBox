<script setup lang="ts">
// 文件说明：前端可复用界面组件。
import type { DialogTitleProps } from "reka-ui"
import type { HTMLAttributes } from "vue"
import { reactiveOmit } from "@vueuse/core"
import { DialogTitle, useForwardProps } from "reka-ui"
import { cn } from "@/lib/utils"

// 组件输入参数。
const props = defineProps<DialogTitleProps & { class?: HTMLAttributes["class"] }>()

// 去除扩展字段后的透传参数。
const delegatedProps = reactiveOmit(props, "class")

// 透传到基础组件的参数。
const forwardedProps = useForwardProps(delegatedProps)
</script>

<template>
  <DialogTitle
    v-bind="forwardedProps"
    :class="
      cn(
        'text-lg font-semibold leading-none tracking-tight',
        props.class,
      )
    "
  >
    <slot />
  </DialogTitle>
</template>
