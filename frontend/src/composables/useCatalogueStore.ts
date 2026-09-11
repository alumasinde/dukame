import { ref, watch, type Ref } from 'vue'
import { catalogueApi, type Store } from '../lib/catalogue'
import type { Tenant } from '../stores/auth'

export function useCatalogueStore(activeTenant: Ref<Tenant | null>) {
  const store = ref<Store | null>(null)
  const loading = ref(false)
  const error = ref('')

  async function load() {
    const tenant = activeTenant.value
    if (!tenant) return
    loading.value = true
    error.value = ''
    try {
      store.value = (await catalogueApi.getStore(tenant.public_id)).data
    } catch (err: any) {
      store.value = null
      if (err?.response?.status !== 404) error.value = err?.response?.data?.detail || 'We could not load the store.'
    } finally {
      loading.value = false
    }
  }

  async function create(payload: { name: string; slug: string; description: string | null; status: string; currency: string }) {
    if (!activeTenant.value) throw new Error('No active shop selected')
    error.value = ''
    store.value = (await catalogueApi.createStore(activeTenant.value.public_id, payload)).data
    return store.value
  }

  watch(activeTenant, load, { immediate: true })

  return { store, loading, error, load, create }
}
