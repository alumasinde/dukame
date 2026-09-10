import { defineStore } from 'pinia'
import { api, clearTokens, getAccessToken, saveTokens } from '../lib/api'

export interface User {
  public_id: string
  email: string
  phone: string | null
  first_name: string
  last_name: string
  is_active: boolean
  is_verified: boolean
}

export interface Tenant {
  public_id: string
  name: string
  slug: string
  status: string
  role: string
}

export const useAuthStore = defineStore('auth', {
  state: () => ({
    user: null as User | null,
    tenants: [] as Tenant[],
    activeTenantId: sessionStorage.getItem('dukame_tenant_public_id') as string | null,
    loading: false,
    initialized: false,
  }),
  getters: {
    isAuthenticated: (state) => Boolean(getAccessToken() && state.user),
    activeTenant: (state) => state.tenants.find((tenant) => tenant.public_id === state.activeTenantId) || state.tenants[0] || null,
  },
  actions: {
    async initialize() {
      if (this.initialized) return
      if (!getAccessToken()) {
        this.initialized = true
        return
      }
      try {
        await this.loadSession()
      } catch {
        this.logoutLocal()
      } finally {
        this.initialized = true
      }
    },
    async loadSession() {
      const [{ data: user }, { data: tenants }] = await Promise.all([
        api.get<User>('/auth/me'),
        api.get<{ items: Tenant[] }>('/tenants'),
      ])
      this.user = user
      this.tenants = tenants.items
      const stored = sessionStorage.getItem('dukame_tenant_public_id')
      const exists = this.tenants.some((tenant) => tenant.public_id === stored)
      this.setActiveTenant(exists ? stored! : this.tenants[0]?.public_id || null)
    },
    async login(email: string, password: string) {
      this.loading = true
      try {
        const { data } = await api.post('/auth/login', { email, password })
        saveTokens(data.access_token, data.refresh_token)
        await this.loadSession()
      } finally {
        this.loading = false
      }
    },
    async register(payload: { email: string; password: string; first_name: string; last_name: string; phone?: string }) {
      this.loading = true
      try {
        await api.post('/auth/register', payload)
        await this.login(payload.email, payload.password)
      } finally {
        this.loading = false
      }
    },
    setActiveTenant(publicId: string | null) {
      this.activeTenantId = publicId
      if (publicId) sessionStorage.setItem('dukame_tenant_public_id', publicId)
      else sessionStorage.removeItem('dukame_tenant_public_id')
    },
    logoutLocal() {
      clearTokens()
      this.user = null
      this.tenants = []
      this.activeTenantId = null
    },
    async logout() {
      try { await api.post('/auth/logout') } finally { this.logoutLocal() }
    },
  },
})