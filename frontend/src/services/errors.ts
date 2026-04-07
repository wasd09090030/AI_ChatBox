import axios, { type AxiosError } from 'axios'

function readMessageFromUnknownData(data: unknown): string | undefined {
  if (!data || typeof data !== 'object') {
    return undefined
  }

  if ('detail' in data && typeof data.detail === 'string') {
    return data.detail
  }

  if ('message' in data && typeof data.message === 'string') {
    return data.message
  }

  return undefined
}

export interface AppError {
  name: 'AppError'
  code: string
  message: string
  status?: number
  details?: unknown
}

export function createAppError(
  message: string,
  code = 'UNKNOWN_ERROR',
  status?: number,
  details?: unknown
): AppError {
  return {
    name: 'AppError',
    code,
    message,
    status,
    details,
  }
}

export function normalizeApiError(error: unknown): AppError {
  if (isAppError(error)) {
    return error
  }

  if (axios.isAxiosError(error)) {
    const axiosError = error as AxiosError<unknown>
    const status = axiosError.response?.status
    const responseData = axiosError.response?.data
    const message = readMessageFromUnknownData(responseData) || axiosError.message || '网络请求失败'

    return createAppError(
      String(message),
      `HTTP_${status || 'UNKNOWN'}`,
      status,
      responseData
    )
  }

  if (error instanceof Error) {
    return createAppError(error.message)
  }

  return createAppError('未知错误')
}

export function isAppError(error: unknown): error is AppError {
  return Boolean(
    error &&
      typeof error === 'object' &&
      'name' in error &&
      (error as AppError).name === 'AppError'
  )
}
