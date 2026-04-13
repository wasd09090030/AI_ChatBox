/**
 * 文件说明：前端状态管理与会话数据维护。
 */

import { defineStore } from 'pinia'
import { ref } from 'vue'

export type FeedbackType = 'success' | 'error' | 'info'

// useFeedbackStore 状态仓库实例。
export const useFeedbackStore = defineStore('feedback', () => {
  const visible = ref(false)
  const message = ref('')
  const type = ref<FeedbackType>('info')
  let timer: ReturnType<typeof setTimeout> | null = null

  function show(nextMessage: string, nextType: FeedbackType = 'info', duration = 3200) {
    if (timer) {
      clearTimeout(timer)
      timer = null
    }

    message.value = nextMessage
    type.value = nextType
    visible.value = true

    timer = setTimeout(() => {
      visible.value = false
    }, duration)
  }

  function showError(nextMessage: string) {
    show(nextMessage, 'error')
  }

  function showSuccess(nextMessage: string) {
    show(nextMessage, 'success')
  }

  function hide() {
    visible.value = false
    if (timer) {
      clearTimeout(timer)
      timer = null
    }
  }

  return {
    visible,
    message,
    type,
    show,
    showError,
    showSuccess,
    hide,
  }
})
