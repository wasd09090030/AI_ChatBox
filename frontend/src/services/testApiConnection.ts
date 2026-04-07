/**
 * Test API Connection Service
 *
 * 通过后端代理验证指定 provider 的 API Key 与 Base URL 的连通性。
 * 前端不持有真实 Key（configStore 只存脱敏预览），
 * 真实 Key 由后端从数据库解密后发起探测请求。
 */

import { API_PREFIX } from '@/utils/constants'
import { getUserId } from '@/domains/user/api/userIdentity'

export type ConnectionStatus = 'ok' | 'unauthorized' | 'not_found' | 'timeout' | 'network_error' | 'no_key' | 'no_base_url' | 'unknown'

export interface TestConnectionResult {
  /** 连接是否成功（API Key 有效且端点可达） */
  success: boolean
  /** 状态码标识，便于前端做差异化提示 */
  status: ConnectionStatus
  /** 可直接展示给用户的消息 */
  message: string
  /** 请求往返时间（毫秒） */
  latencyMs?: number
}

/**
 * 测试指定 provider 的 API 连接与 Key 合法性。
 *
 * 后端端点：POST /api/v2/providers/test-connection
 * 后端负责从 DB 解密真实 Key 并发起探测请求。
 *
 * @param provider      - Provider 标识（如 'deepseek'、'openai'）
 * @param baseUrlOverride - 可选的 Base URL 覆盖（用于用户刚输入但尚未保存的 URL）
 */
export async function testApiConnection(
  provider: string,
  baseUrlOverride?: string,
): Promise<TestConnectionResult> {
  try {
    const body: Record<string, string> = { provider }
    if (baseUrlOverride?.trim()) {
      body.base_url = baseUrlOverride.trim()
    }

    const resp = await fetch(`${API_PREFIX}/providers/test-connection`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-User-ID': getUserId(),
      },
      body: JSON.stringify(body),
    })

    if (!resp.ok) {
      const text = await resp.text().catch(() => '')
      return {
        success: false,
        status: 'unknown',
        message: `后端返回错误（HTTP ${resp.status}）：${text.slice(0, 200)}`,
      }
    }

    const data = await resp.json()
    return {
      success: data.success,
      status: (data.status ?? 'unknown') as ConnectionStatus,
      message: data.message ?? '',
      latencyMs: data.latency_ms,
    }
  } catch (err: unknown) {
    const msg = err instanceof Error ? err.message : String(err)
    return { success: false, status: 'network_error', message: `请求失败：${msg}` }
  }
}
