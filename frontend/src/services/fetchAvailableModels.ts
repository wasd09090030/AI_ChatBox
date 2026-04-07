/**
 * Fetch Available Models Service
 *
 * 通过后端代理查询指定 provider 支持的模型列表。
 * 前端不持有真实 Key，后端从 DB 解密后调用远端 /models 接口。
 * 若远端调用失败，后端会降级返回预置模型列表。
 */

import { API_PREFIX } from '@/utils/constants'
import { getUserId } from '@/domains/user/api/userIdentity'

export interface ModelInfo {
  id: string
  object?: string
  created?: number
  owned_by?: string
}

export interface FetchModelsResult {
  success: boolean
  /** 数据来源：'remote' = 实际从 API 获取；'preset' = 降级使用预置列表 */
  source?: 'remote' | 'preset'
  models: ModelInfo[]
  error?: string
}

/**
 * 查询指定 provider 支持的模型列表。
 *
 * 后端端点：GET /api/v2/providers/{provider}/models
 *
 * @param provider      - Provider 标识（如 'deepseek'、'openai'）
 * @param baseUrlOverride - 可选的 Base URL 覆盖（用于用户刚输入但尚未保存的 URL）
 */
export async function fetchAvailableModels(
  provider: string,
  baseUrlOverride?: string,
): Promise<FetchModelsResult> {
  try {
    const params = new URLSearchParams()
    if (baseUrlOverride?.trim()) {
      params.set('base_url', baseUrlOverride.trim())
    }
    const query = params.toString() ? `?${params}` : ''

    const resp = await fetch(
      `${API_PREFIX}/providers/${encodeURIComponent(provider)}/models${query}`,
      {
        method: 'GET',
        headers: { 'X-User-ID': getUserId() },
      },
    )

    if (!resp.ok) {
      const text = await resp.text().catch(() => '')
      return {
        success: false,
        models: [],
        error: `后端返回错误（HTTP ${resp.status}）：${text.slice(0, 200)}`,
      }
    }

    const data = await resp.json()
    const rawModels: { id: string }[] = data.models ?? []

    return {
      success: true,
      source: data.source ?? 'remote',
      models: rawModels.map((m) => ({ id: m.id, object: 'model' })),
    }
  } catch (err: unknown) {
    const msg = err instanceof Error ? err.message : String(err)
    return { success: false, models: [], error: `请求失败：${msg}` }
  }
}
