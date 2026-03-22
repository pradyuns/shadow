import axios from 'axios'

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1',
  headers: { 'Content-Type': 'application/json' },
  withCredentials: true,
})

let isRefreshing = false

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

export function extractApiErrorMessage(error: unknown, fallback: string) {
  if (axios.isAxiosError(error)) {
    const detail = error.response?.data?.detail
    if (typeof detail === 'string') return detail
  }

  return fallback
}

export default api
