import axios, { type AxiosError, type InternalAxiosRequestConfig } from 'axios'

const apiBaseUrl = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1'

const api = axios.create({
  baseURL: apiBaseUrl,
  timeout: 15000,
  headers: { 'Content-Type': 'application/json' },
})

// Log API configuration in development
if (import.meta.env.DEV) {
  console.log('[DukaMe API] Base URL:', apiBaseUrl)
}

let refreshPromise: Promise<string | null> | null = null

function getAccessToken() {
  return sessionStorage.getItem('dukame_access_token')
}

function getRefreshToken() {
  return sessionStorage.getItem('dukame_refresh_token')
}

function saveTokens(accessToken: string, refreshToken: string) {
  sessionStorage.setItem('dukame_access_token', accessToken)
  sessionStorage.setItem('dukame_refresh_token', refreshToken)
}

function clearTokens() {
  sessionStorage.removeItem('dukame_access_token')
  sessionStorage.removeItem('dukame_refresh_token')
  sessionStorage.removeItem('dukame_tenant_public_id')
}

function getRequestId(headers: any) {
  return headers['x-request-id'] || 'unknown'
}

api.interceptors.request.use((config: InternalAxiosRequestConfig) => {
  const token = getAccessToken()
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

api.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const original = error.config as (InternalAxiosRequestConfig & { _retry?: boolean }) | undefined

    // Log network errors in development
    if (import.meta.env.DEV && !error.response) {
      console.error('[DukaMe API] Network error:', {
        message: error.message,
        code: error.code,
        config: { baseURL: error.config?.baseURL, url: error.config?.url },
      })
    }

    // Only retry on 401 with valid refresh token
    if (error.response?.status !== 401 || !original || original._retry || !getRefreshToken()) {
      return Promise.reject(error)
    }

    original._retry = true

    // Deduplicate refresh requests
    if (!refreshPromise) {
      refreshPromise = api
        .post('/auth/refresh', { refresh_token: getRefreshToken() })
        .then(({ data }) => {
          saveTokens(data.access_token, data.refresh_token)
          return data.access_token as string
        })
        .catch((refreshError) => {
          clearTokens()
          return null
        })
        .finally(() => {
          refreshPromise = null
        })
    }

    const token = await refreshPromise
    if (!token) {
      window.dispatchEvent(new CustomEvent('dukame:session-expired'))
      return Promise.reject(error)
    }

    // Retry original request with new token
    original.headers.Authorization = `Bearer ${token}`
    return api.request(original)
  },
)

export { api, saveTokens, clearTokens, getAccessToken, getRefreshToken, getRequestId }
