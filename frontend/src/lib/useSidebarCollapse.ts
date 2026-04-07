import { onMounted, ref, watch } from 'vue'

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
