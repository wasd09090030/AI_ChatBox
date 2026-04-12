/**
 * 文件说明：前端业务域逻辑与接口封装。
 */

const CURRENT_USER_ID_KEY = 'storybox_user_id'
// 变量作用：变量 LEGACY_USER_ID_KEY，用于 LEGACY USER ID KEY 相关配置或状态。
const LEGACY_USER_ID_KEY = 'chatbox_user_id'

/** 功能：函数 getUserId，负责 getUserId 相关处理。 */
export function getUserId(): string {
  const currentUserId = localStorage.getItem(CURRENT_USER_ID_KEY)
  if (currentUserId) {
    return currentUserId
  }

  const legacyUserId = localStorage.getItem(LEGACY_USER_ID_KEY)
  if (legacyUserId) {
    localStorage.setItem(CURRENT_USER_ID_KEY, legacyUserId)
    localStorage.removeItem(LEGACY_USER_ID_KEY)
    return legacyUserId
  }

  const createdUserId = `user_${Date.now()}_${Math.random().toString(36).slice(2, 11)}`
  localStorage.setItem(CURRENT_USER_ID_KEY, createdUserId)
  return createdUserId
}

/** 功能：函数 getUserHeaders，负责 getUserHeaders 相关处理。 */
export function getUserHeaders(): Record<string, string> {
  return {
    'X-User-ID': getUserId(),
  }
}
