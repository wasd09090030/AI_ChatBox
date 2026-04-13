<script setup lang="ts">
// 文件说明：前端可复用界面组件。
import type { DropdownMenuSeparatorProps } from "reka-ui"
import type { HTMLAttributes } from "vue"
import { reactiveOmit } from "@vueuse/core"
import {
  DropdownMenuSeparator,
} from "reka-ui"
import { cn } from "@/lib/utils"

// 组件输入参数。
const props = defineProps<DropdownMenuSeparatorProps & {
  class?: HTMLAttributes["class"]
}>()

// 去除扩展字段后的透传参数。
const delegatedProps = reactiveOmit(props, "class")
</script>

<template>
  <DropdownMenuSeparator v-bind="delegatedProps" :class="cn('-mx-1 my-1 h-px bg-muted', props.class)" />
</template>
