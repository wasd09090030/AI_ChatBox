/**
 * 文件说明：前端工具函数与辅助逻辑。
 */

import { DEFAULT_ROLES } from '@/config/prompts'

// API Configuration
export const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL as string | undefined)?.trim() ?? ''
// 常量 API_VERSION。
export const API_VERSION = 'v2'
// 常量 API_PREFIX。
export const API_PREFIX = API_BASE_URL
  ? `${API_BASE_URL}/api/${API_VERSION}`
  : `/api/${API_VERSION}`

// Storage Keys
export const STORAGE_KEYS = {
  API_KEYS: 'api_keys',
  USER_CONFIG: 'user_config',
  CONVERSATIONS: 'conversations',
  ROLES: 'roles',
  THEME: 'theme',
} as const

// AI Models
export const AI_MODELS = {
  OPENAI: {
    'gpt-4': 'GPT-4',
    'gpt-4-turbo': 'GPT-4 Turbo',
    'gpt-3.5-turbo': 'GPT-3.5 Turbo',
  },
  ANTHROPIC: {
    'claude-3-opus': 'Claude 3 Opus',
    'claude-3-sonnet': 'Claude 3 Sonnet',
    'claude-3-haiku': 'Claude 3 Haiku',
  },
  DEEPSEEK: {
    'deepseek-chat': 'DeepSeek Chat',
    'deepseek-coder': 'DeepSeek Coder',
  },
} as const

// Message Roles
export const MESSAGE_ROLES = {
  USER: 'user',
  ASSISTANT: 'assistant',
  SYSTEM: 'system',
} as const

export { DEFAULT_ROLES }
