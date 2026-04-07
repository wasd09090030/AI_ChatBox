import type { ProviderKey } from '@/utils/types'

export interface ProviderModelOption {
  value: string
  label: string
}

export interface ProviderMeta {
  key: ProviderKey
  name: string
  color: string
  placeholder: string
  docsUrl: string
  defaultBaseUrl: string
  models: ProviderModelOption[]
}

export interface ToneInfo {
  tone: string
  offset: number
  label: string
  matched: boolean
}
