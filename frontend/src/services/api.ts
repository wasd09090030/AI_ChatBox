/**
 * Base API Configuration
 *
 * Axios instance with interceptors for error handling
 */

import axios, { type AxiosInstance, type AxiosError } from 'axios'
import { API_PREFIX } from '@/utils/constants'
import { normalizeApiError } from './errors'

// Create axios instance
const api: AxiosInstance = axios.create({
  baseURL: API_PREFIX,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Request interceptor
api.interceptors.request.use(
  (config) => {
    // Add any auth tokens or custom headers here
    return config
  },
  (error: AxiosError) => {
    console.error('Request error:', error)
    return Promise.reject(normalizeApiError(error))
  }
)

// Response interceptor
api.interceptors.response.use(
  (response) => {
    return response
  },
  (error: AxiosError) => {
    // Handle different error types
    if (error.response) {
      // Server responded with error status
      const { status, data } = error.response

      switch (status) {
        case 400:
          console.error('Bad Request:', data)
          break
        case 401:
          console.error('Unauthorized:', data)
          break
        case 403:
          console.error('Forbidden:', data)
          break
        case 404:
          console.error('Not Found:', data)
          break
        case 500:
          console.error('Server Error:', data)
          break
        default:
          console.error('API Error:', data)
      }
    } else if (error.request) {
      // Request made but no response
      console.error('Network Error: No response from server')
    } else {
      // Error in request setup
      console.error('Request Error:', error.message)
    }

    return Promise.reject(error)
  }
)

export default api
