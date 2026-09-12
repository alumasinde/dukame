import axios, { type AxiosError, type InternalAxiosRequestConfig } from 'axios'
import { APP_NAME } from './branding'

const apiBaseUrl = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1'

const api = axios.create({
  baseURL: apiBaseUrl,
  timeout: 15000,
  headers: { 'Content-Type': 'application/json' },
})

const refreshClient = axios.create({
  baseURL: apiBaseUrl,
  timeout: 15000,
  headers: { 'Content-Type': 'application/json' },
})

if (import.meta.env.DEV) console.log(`[${APP_NAME} API] Base URL:`, apiBaseUrl)

let refreshPromise: Promise<string | null> | null = null

type RetriableRequest = InternalAxiosRequestConfig & { _retry?: boolean }

function getAccessToken(): string | null { return sessionStorage.getItem('dukame_access_token') }
function getRefreshToken(): string | null { return sessionStorage.getItem('dukame_refresh_token') }
function saveTokens(accessToken: string, refreshToken: string): void {
  sessionStorage.setItem('dukame_access_token', accessToken)
  sessionStorage.setItem('dukame_refresh_token', refreshToken)
}
function clearTokens(): void {
  sessionStorage.removeItem('dukame_access_token')
  sessionStorage.removeItem('dukame_refresh_token')
  sessionStorage.removeItem('dukame_tenant_public_id')
}
function getRequestId(headers: Record<string, unknown> | undefined): string {
  const value = headers?.['x-request-id']
  return typeof value === 'string' ? value : 'unknown'
}

api.interceptors.request.use((config: InternalAxiosRequestConfig) => {
  const token = getAccessToken()
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

async function refreshAccessToken(): Promise<string | null> {
  const refreshToken = getRefreshToken()
  if (!refreshToken) return null
  if (!refreshPromise) {
    refreshPromise = refreshClient
      .post('/auth/refresh', { refresh_token: refreshToken })
      .then(({ data }) => {
        if (typeof data?.access_token !== 'string' || typeof data?.refresh_token !== 'string') throw new Error('Invalid token response')
        saveTokens(data.access_token, data.refresh_token)
        return data.access_token
      })
      .catch(() => {
        clearTokens()
        return null
      })
      .finally(() => { refreshPromise = null })
  }
  return refreshPromise
}

api.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const original = error.config as RetriableRequest | undefined
    if (import.meta.env.DEV && !error.response) {
      console.error(`[${APP_NAME} API] Network error:`, { message: error.message, code: error.code, config: { baseURL: error.config?.baseURL, url: error.config?.url } })
    }
    if (error.response?.status !== 401 || !original || original._retry || !getRefreshToken() || original.url?.endsWith('/auth/refresh')) return Promise.reject(error)
    original._retry = true
    const token = await refreshAccessToken()
    if (!token) {
      window.dispatchEvent(new CustomEvent('dukame:session-expired'))
      return Promise.reject(error)
    }
    original.headers.Authorization = `Bearer ${token}`
    return api.request(original)
  },
)

export { api, saveTokens, clearTokens, getAccessToken, getRefreshToken, getRequestId }
