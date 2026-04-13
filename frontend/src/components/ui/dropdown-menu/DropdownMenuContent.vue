<script setup lang="ts">
// 文件说明：前端可复用界面组件。
import type { DropdownMenuContentEmits, DropdownMenuContentProps } from "reka-ui"
import type { HTMLAttributes } from "vue"
import { reactiveOmit } from "@vueuse/core"
import {
  DropdownMenuContent,
  DropdownMenuPortal,
  useForwardPropsEmits,
} from "reka-ui"
import { cn } from "@/lib/utils"

// 组件输入参数。
const props = withDefaults(
  defineProps<DropdownMenuContentProps & { class?: HTMLAttributes["class"] }>(),
  {
    sideOffset: 4,
  },
)
// 组件事件声明。
const emits = defineEmits<DropdownMenuContentEmits>()

// 去除扩展字段后的透传参数。
const delegatedProps = reactiveOmit(props, "class")

// 透传到基础组件的参数与事件。
const forwarded = useForwardPropsEmits(delegatedProps, emits)
</script>

<template>
  <DropdownMenuPortal>
    <DropdownMenuContent
      v-bind="forwarded"
      :class="cn('z-50 min-w-32 overflow-hidden rounded-md border bg-popover p-1 text-popover-foreground shadow-md data-[state=open]:animate-in data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=open]:fade-in-0 data-[state=closed]:zoom-out-95 data-[state=open]:zoom-in-95 data-[side=bottom]:slide-in-from-top-2 data-[side=left]:slide-in-from-right-2 data-[side=right]:slide-in-from-left-2 data-[side=top]:slide-in-from-bottom-2', props.class)"
    >
      <slot />
    </DropdownMenuContent>
  </DropdownMenuPortal>
</template>
