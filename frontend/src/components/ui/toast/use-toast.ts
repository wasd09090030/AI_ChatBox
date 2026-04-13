/**
 * 文件说明：前端可复用界面组件。
 */

import type { Component, VNode } from "vue"
import type { ToastProps } from "."
import { computed, ref } from "vue"

// 常量 TOAST_LIMIT。
const TOAST_LIMIT = 1
// 常量 TOAST_REMOVE_DELAY。
const TOAST_REMOVE_DELAY = 1000000

export type StringOrVNode
  = | string
    | VNode
    | (() => VNode)

type ToasterToast = ToastProps & {
  id: string
  title?: string
  description?: StringOrVNode
  action?: Component
}

// actionTypes 相关状态。
const actionTypes = {
  ADD_TOAST: "ADD_TOAST",
  UPDATE_TOAST: "UPDATE_TOAST",
  DISMISS_TOAST: "DISMISS_TOAST",
  REMOVE_TOAST: "REMOVE_TOAST",
} as const

// count 相关状态。
let count = 0

/** 处理 genId 相关逻辑。 */
function genId() {
  count = (count + 1) % Number.MAX_VALUE
  return count.toString()
}

type ActionType = typeof actionTypes

type Action
  = | {
    type: ActionType["ADD_TOAST"]
    toast: ToasterToast
  }
  | {
    type: ActionType["UPDATE_TOAST"]
    toast: Partial<ToasterToast>
  }
  | {
    type: ActionType["DISMISS_TOAST"]
    toastId?: ToasterToast["id"]
  }
  | {
    type: ActionType["REMOVE_TOAST"]
    toastId?: ToasterToast["id"]
  }

interface State {
  toasts: ToasterToast[]
}

// toastTimeouts 相关状态。
const toastTimeouts = new Map<string, ReturnType<typeof setTimeout>>()

/** 处理 addToRemoveQueue 相关逻辑。 */
function addToRemoveQueue(toastId: string) {
  if (toastTimeouts.has(toastId))
    return

  const timeout = setTimeout(() => {
    toastTimeouts.delete(toastId)
    dispatch({
      type: actionTypes.REMOVE_TOAST,
      toastId,
    })
  }, TOAST_REMOVE_DELAY)

  toastTimeouts.set(toastId, timeout)
}

// 组件内部状态。
const state = ref<State>({
  toasts: [],
})

/** 处理 dispatch 相关逻辑。 */
function dispatch(action: Action) {
  switch (action.type) {
    case actionTypes.ADD_TOAST:
      state.value.toasts = [action.toast, ...state.value.toasts].slice(0, TOAST_LIMIT)
      break

    case actionTypes.UPDATE_TOAST:
      state.value.toasts = state.value.toasts.map(t =>
        t.id === action.toast.id ? { ...t, ...action.toast } : t,
      )
      break

    case actionTypes.DISMISS_TOAST: {
      const { toastId } = action

      if (toastId) {
        addToRemoveQueue(toastId)
      }
      else {
        state.value.toasts.forEach((toast) => {
          addToRemoveQueue(toast.id)
        })
      }

      state.value.toasts = state.value.toasts.map(t =>
        t.id === toastId || toastId === undefined
          ? {
              ...t,
              open: false,
            }
          : t,
      )
      break
    }

    case actionTypes.REMOVE_TOAST:
      if (action.toastId === undefined)
        state.value.toasts = []
      else
        state.value.toasts = state.value.toasts.filter(t => t.id !== action.toastId)

      break
  }
}

/** 处理 useToast 相关逻辑。 */
function useToast() {
  return {
    toasts: computed(() => state.value.toasts),
    toast,
    dismiss: (toastId?: string) => dispatch({ type: actionTypes.DISMISS_TOAST, toastId }),
  }
}

type Toast = Omit<ToasterToast, "id">

/** 处理 toast 相关逻辑。 */
function toast(props: Toast) {
  const id = genId()

  const update = (props: ToasterToast) =>
    dispatch({
      type: actionTypes.UPDATE_TOAST,
      toast: { ...props, id },
    })

  const dismiss = () => dispatch({ type: actionTypes.DISMISS_TOAST, toastId: id })

  dispatch({
    type: actionTypes.ADD_TOAST,
    toast: {
      ...props,
      id,
      open: true,
      onOpenChange: (open: boolean) => {
        if (!open)
          dismiss()
      },
    },
  })

  return {
    id,
    dismiss,
    update,
  }
}

export { toast, useToast }
