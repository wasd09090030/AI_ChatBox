<script setup lang="ts">
// 文件说明：前端可复用界面组件。
import type { DropdownMenuLabelProps } from "reka-ui"
import type { HTMLAttributes } from "vue"
import { reactiveOmit } from "@vueuse/core"
import { DropdownMenuLabel, useForwardProps } from "reka-ui"
import { cn } from "@/lib/utils"

// 组件输入参数。
const props = defineProps<DropdownMenuLabelProps & { class?: HTMLAttributes["class"], inset?: boolean }>()

// 去除扩展字段后的透传参数。
const delegatedProps = reactiveOmit(props, "class")

// 透传到基础组件的参数。
const forwardedProps = useForwardProps(delegatedProps)
</script>

<template>
  <DropdownMenuLabel
    v-bind="forwardedProps"
    :class="cn('px-2 py-1.5 text-sm font-semibold', inset && 'pl-8', props.class)"
  >
    <slot />
  </DropdownMenuLabel>
</template>
