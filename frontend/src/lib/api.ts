import axios from 'axios'

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1',
  headers: { 'Content-Type': 'application/json' },
  withCredentials: true,
})

// prevent concurrent refresh attempts from racing
let isRefreshing = false

// auto-refresh expired access tokens, redirect to login on failure
api.interceptors.response.use(
  (res) => res,
  async (err) => {
    const originalRequest = err.config as (typeof err.config & { _retry?: boolean }) | undefined
    const requestPath = originalRequest?.url || ''

    if (
      err.response?.status === 401 &&
      originalRequest &&
      !originalRequest._retry &&
      !requestPath.includes('/auth/login') &&
      !requestPath.includes('/auth/register') &&
      !requestPath.includes('/auth/refresh')
    ) {
      originalRequest._retry = true

      if (!isRefreshing) {
        isRefreshing = true
        try {
          await api.post('/auth/refresh')
          isRefreshing = false
          return api(originalRequest)
        } catch {
          isRefreshing = false
        }
      }

      window.location.href = '/login'
    }

    return Promise.reject(err)
  },
)

// pull the detail string from an axios error response, or fall back to a default
export function extractApiErrorMessage(error: unknown, fallback: string) {
  if (axios.isAxiosError(error)) {
    const detail = error.response?.data?.detail
    if (typeof detail === 'string') return detail
  }

  return fallback
}

export default api
