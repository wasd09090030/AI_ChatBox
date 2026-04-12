<script setup lang="ts">
// 文件说明：前端可复用界面组件。
import type { DropdownMenuRadioItemEmits, DropdownMenuRadioItemProps } from "reka-ui"
import type { HTMLAttributes } from "vue"
import { reactiveOmit } from "@vueuse/core"
import { Circle } from "lucide-vue-next"
import {
  DropdownMenuItemIndicator,
  DropdownMenuRadioItem,
  useForwardPropsEmits,
} from "reka-ui"
import { cn } from "@/lib/utils"

// 变量作用：变量 props，用于 props 相关配置或状态。
const props = defineProps<DropdownMenuRadioItemProps & { class?: HTMLAttributes["class"] }>()

// 变量作用：变量 emits，用于 emits 相关配置或状态。
const emits = defineEmits<DropdownMenuRadioItemEmits>()

// 变量作用：变量 delegatedProps，用于 delegatedProps 相关配置或状态。
const delegatedProps = reactiveOmit(props, "class")

// 变量作用：变量 forwarded，用于 forwarded 相关配置或状态。
const forwarded = useForwardPropsEmits(delegatedProps, emits)
</script>

<template>
  <DropdownMenuRadioItem
    v-bind="forwarded"
    :class="cn(
      'relative flex cursor-default select-none items-center rounded-sm py-1.5 pl-8 pr-2 text-sm outline-none transition-colors focus:bg-accent focus:text-accent-foreground data-[disabled]:pointer-events-none data-[disabled]:opacity-50',
      props.class,
    )"
  >
    <span class="absolute left-2 flex h-3.5 w-3.5 items-center justify-center">
      <DropdownMenuItemIndicator>
        <Circle class="h-4 w-4 fill-current" />
      </DropdownMenuItemIndicator>
    </span>
    <slot />
  </DropdownMenuRadioItem>
</template>
