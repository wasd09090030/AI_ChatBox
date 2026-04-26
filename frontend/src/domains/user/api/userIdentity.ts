/**
 * 文件说明：前端业务域逻辑与接口封装。
 */

const LEGACY_USER_ID_KEYS = ['storybox_user_id', 'chatbox_user_id'] as const

/** 读取旧匿名身份标记，仅用于一次性认领迁移。 */
export function getLegacyUserId(): string | null {
  for (const key of LEGACY_USER_ID_KEYS) {
    const value = localStorage.getItem(key)
    if (value) {
      return value
    }
  }
  return null
}

/** 清理旧匿名身份标记，避免其继续参与后续流程。 */
export function clearLegacyUserId() {
  LEGACY_USER_ID_KEYS.forEach((key) => localStorage.removeItem(key))
}
