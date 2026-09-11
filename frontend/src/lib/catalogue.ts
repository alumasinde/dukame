import { api } from './api'

export interface Store {
  public_id: string
  name: string
  slug: string
  description: string | null
  status: string
  currency: string
}

export interface Category {
  public_id: string
  name: string
  slug: string
  description: string | null
  parent_public_id: string | null
  status: string
  sort_order: number
}

export interface Product {
  public_id: string
  name: string
  slug: string
  description: string | null
  category_public_id: string | null
  sku: string | null
  price_minor: number
  compare_at_price_minor: number | null
  currency: string
  inventory_tracking: boolean
  inventory_quantity: number
  status: string
}

export const catalogueApi = {
  getStore(tenantId: string) {
    return api.get<Store>(`/tenants/${tenantId}/store`)
  },
  createStore(tenantId: string, payload: Omit<Store, 'public_id'>) {
    return api.post<Store>(`/tenants/${tenantId}/store`, payload)
  },
  listCategories(tenantId: string) {
    return api.get<Category[]>(`/tenants/${tenantId}/categories`, { params: { limit: 100 } })
  },
  createCategory(tenantId: string, payload: Record<string, unknown>) {
    return api.post<Category>(`/tenants/${tenantId}/categories`, payload)
  },
  updateCategory(tenantId: string, id: string, payload: Record<string, unknown>) {
    return api.put<Category>(`/tenants/${tenantId}/categories/${id}`, payload)
  },
  deleteCategory(tenantId: string, id: string) {
    return api.delete(`/tenants/${tenantId}/categories/${id}`)
  },
  listProducts(tenantId: string) {
    return api.get<Product[]>(`/tenants/${tenantId}/products`, { params: { limit: 100 } })
  },
  createProduct(tenantId: string, payload: Record<string, unknown>) {
    return api.post<Product>(`/tenants/${tenantId}/products`, payload)
  },
  updateProduct(tenantId: string, id: string, payload: Record<string, unknown>) {
    return api.put<Product>(`/tenants/${tenantId}/products/${id}`, payload)
  },
  deleteProduct(tenantId: string, id: string) {
    return api.delete(`/tenants/${tenantId}/products/${id}`)
  },
}
