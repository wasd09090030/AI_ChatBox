/**
 * 文件说明：项目文件 useSidebarCollapse.ts 的核心逻辑实现。
 */

import { onMounted, ref, watch } from 'vue'

/** 处理 useSidebarCollapse 相关逻辑。 */
export function useSidebarCollapse(storageKey: string, defaultValue = false) {
  const collapsed = ref(defaultValue)

  onMounted(() => {
    if (typeof window === 'undefined') return

    const storedValue = window.localStorage.getItem(storageKey)
    if (storedValue === null) return

    collapsed.value = storedValue === 'true'
  })

  watch(collapsed, (value) => {
    if (typeof window === 'undefined') return
    window.localStorage.setItem(storageKey, value ? 'true' : 'false')
  })

  return collapsed
}
