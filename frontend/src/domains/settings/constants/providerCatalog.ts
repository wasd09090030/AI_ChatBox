/**
 * 文件说明：前端业务域逻辑与接口封装。
 */

import type { ProviderMeta, ToneInfo } from '@/components/config/types'

export const TONE_TEMP_OFFSET: Record<string, { offset: number; label: string }> = {
  dark: { offset: -0.15, label: '黑暗' },
  serious: { offset: -0.15, label: '严肃' },
  tense: { offset: -0.15, label: '紧张' },
  horror: { offset: -0.10, label: '恐怖' },
  mystery: { offset: -0.05, label: '悬疑' },
  romantic: { offset: +0.10, label: '浪漫' },
  humorous: { offset: +0.10, label: '幽默' },
  comedy: { offset: +0.10, label: '喜剧' },
  epic: { offset: +0.05, label: '史诗' },
  intimate: { offset: +0.05, label: '亲密' },
}

export const PROVIDERS: ProviderMeta[] = [
  {
    key: 'deepseek',
    name: 'DeepSeek',
    color: 'bg-blue-500',
    placeholder: 'sk-...',
    docsUrl: 'https://platform.deepseek.com/api_keys',
    defaultBaseUrl: 'https://api.deepseek.com',
    models: [
      { value: 'deepseek-chat', label: 'DeepSeek Chat (推荐)' },
      { value: 'deepseek-reasoner', label: 'DeepSeek Reasoner' },
    ],
  },
  {
    key: 'qwen',
    name: 'Qwen 通义千问',
    color: 'bg-purple-500',
    placeholder: 'sk-...',
    docsUrl: 'https://dashscope.console.aliyun.com/apiKey',
    defaultBaseUrl: 'https://dashscope.aliyuncs.com/compatible-mode/v1',
    models: [
      { value: 'qwen-plus', label: 'Qwen Plus' },
      { value: 'qwen-turbo', label: 'Qwen Turbo' },
      { value: 'qwen-max', label: 'Qwen Max' },
      { value: 'qwen-long', label: 'Qwen Long' },
    ],
  },
  {
    key: 'openai',
    name: 'OpenAI (GPT)',
    color: 'bg-green-600',
    placeholder: 'sk-...',
    docsUrl: 'https://platform.openai.com/api-keys',
    defaultBaseUrl: 'https://api.openai.com/v1',
    models: [
      { value: 'gpt-4o', label: 'GPT-4o' },
      { value: 'gpt-4o-mini', label: 'GPT-4o Mini' },
      { value: 'gpt-4-turbo', label: 'GPT-4 Turbo' },
      { value: 'gpt-3.5-turbo', label: 'GPT-3.5 Turbo' },
    ],
  },
  {
    key: 'gemini',
    name: 'Google Gemini',
    color: 'bg-amber-500',
    placeholder: 'AIza...',
    docsUrl: 'https://aistudio.google.com/app/apikey',
    defaultBaseUrl: 'https://generativelanguage.googleapis.com/v1beta/openai',
    models: [
      { value: 'gemini-2.0-flash', label: 'Gemini 2.0 Flash' },
      { value: 'gemini-1.5-pro', label: 'Gemini 1.5 Pro' },
      { value: 'gemini-1.5-flash', label: 'Gemini 1.5 Flash' },
    ],
  },
  {
    key: 'anthropic',
    name: 'Anthropic Claude',
    color: 'bg-orange-500',
    placeholder: 'sk-ant-...',
    docsUrl: 'https://console.anthropic.com/settings/keys',
    defaultBaseUrl: 'https://api.anthropic.com',
    models: [
      { value: 'claude-3-5-sonnet-20241022', label: 'Claude 3.5 Sonnet' },
      { value: 'claude-3-5-haiku-20241022', label: 'Claude 3.5 Haiku' },
      { value: 'claude-3-opus-20240229', label: 'Claude 3 Opus' },
    ],
  },
  {
    key: 'custom',
    name: '自定义 (OpenAI 兼容)',
    color: 'bg-slate-500',
    placeholder: 'API Key...',
    docsUrl: '',
    defaultBaseUrl: '',
    models: [],
  },
]

/** 处理 resolveToneInfo 相关逻辑。 */
export function resolveToneInfo(tone: string): ToneInfo | null {
  const normalizedTone = tone.toLowerCase()
  if (!normalizedTone) return null
  const info = TONE_TEMP_OFFSET[normalizedTone]
  if (!info) return { tone: normalizedTone, offset: 0, label: normalizedTone, matched: false }
  return { tone: normalizedTone, ...info, matched: true }
}
