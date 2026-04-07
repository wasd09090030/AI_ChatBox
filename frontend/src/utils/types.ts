// Role Types
export interface Role {
  id: string
  name: string
  description: string
  systemPrompt: string
  icon: string
}

// API Key Types
export type ProviderKey = 'openai' | 'anthropic' | 'deepseek' | 'qwen' | 'gemini' | 'custom'
export type SceneModelKey = 'story_generation' | 'input_enhancement' | 'story_adjustment'

export interface APIKeys {
  openai?: string
  anthropic?: string
  deepseek?: string
  qwen?: string
  gemini?: string
  custom?: string
}

/** Custom base URL overrides per provider. Empty/undefined = use provider default. */
export interface ProviderBaseUrls {
  openai?: string
  anthropic?: string
  deepseek?: string
  qwen?: string
  gemini?: string
  custom?: string   // required for 'custom' provider
}

// User Config Types
export interface UserConfig {
  theme: 'light' | 'dark' | 'system'
  defaultModel: string
  defaultProvider: ProviderKey
  temperature: number
  maxTokens: number
}

export interface SceneModelPreference {
  provider: ProviderKey | ''
  model: string
}

export interface SceneModelPreferences {
  story_generation: SceneModelPreference
  input_enhancement: SceneModelPreference
  story_adjustment: SceneModelPreference
}

// Flutter Bridge Types
export interface FlutterBridgeRequest {
  method: string
  params?: Record<string, unknown>
}

export interface FlutterBridgeResponse {
  success: boolean
  data?: unknown
  error?: string
}
