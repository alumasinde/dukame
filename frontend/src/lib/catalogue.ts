import { api } from './api'

export interface Store { public_id: string; name: string; slug: string; description: string | null; status: string; currency: string; sms_notifications_enabled?: boolean; whatsapp_notifications_enabled?: boolean }
export interface Category { public_id: string; name: string; slug: string; description: string | null; parent_public_id: string | null; status: string; sort_order: number }
export interface Product { public_id: string; name: string; slug: string; description: string | null; category_public_id: string | null; sku: string | null; price_minor: number; compare_at_price_minor: number | null; currency: string; inventory_tracking: boolean; inventory_quantity: number; status: string }
export interface ProductOptionValue { public_id: string; name: string; slug: string; status: string; sort_order: number }
export interface ProductOption { public_id: string; name: string; slug: string; status: string; sort_order: number; values: ProductOptionValue[] }
export interface ProductVariant { public_id: string; sku: string | null; price_minor: number | null; compare_at_price_minor: number | null; inventory_tracking: boolean; inventory_quantity: number; status: string; option_value_public_ids: string[] }
export interface ProductMedia { public_id: string; url: string; alt_text: string | null; media_type: string; sort_order: number; status: string }

export const catalogueApi = {
  getStore(tenantId: string) { return api.get<Store>(`/tenants/${tenantId}/store`) },
  createStore(tenantId: string, payload: Omit<Store, 'public_id'>) { return api.post<Store>(`/tenants/${tenantId}/store`, payload) },
  updateStore(tenantId: string, payload: Partial<Pick<Store, 'name' | 'slug' | 'description' | 'status' | 'currency' | 'sms_notifications_enabled' | 'whatsapp_notifications_enabled'>>) {
    return api.put<Store>(`/tenants/${tenantId}/store`, payload)
  },
  listCategories(tenantId: string) { return api.get<Category[]>(`/tenants/${tenantId}/categories`, { params: { limit: 100 } }) },
  createCategory(tenantId: string, payload: Record<string, unknown>) { return api.post<Category>(`/tenants/${tenantId}/categories`, payload) },
  updateCategory(tenantId: string, id: string, payload: Record<string, unknown>) { return api.put<Category>(`/tenants/${tenantId}/categories/${id}`, payload) },
  deleteCategory(tenantId: string, id: string) { return api.delete(`/tenants/${tenantId}/categories/${id}`) },
  listProducts(tenantId: string) { return api.get<Product[]>(`/tenants/${tenantId}/products`, { params: { limit: 100 } }) },
  getProduct(tenantId: string, id: string) { return api.get<Product>(`/tenants/${tenantId}/products/${id}`) },
  createProduct(tenantId: string, payload: Record<string, unknown>) { return api.post<Product>(`/tenants/${tenantId}/products`, payload) },
  updateProduct(tenantId: string, id: string, payload: Record<string, unknown>) { return api.put<Product>(`/tenants/${tenantId}/products/${id}`, payload) },
  deleteProduct(tenantId: string, id: string) { return api.delete(`/tenants/${tenantId}/products/${id}`) },
  listOptions(tenantId: string, productId: string) { return api.get<ProductOption[]>(`/tenants/${tenantId}/products/${productId}/options`) },
  createOption(tenantId: string, productId: string, payload: Record<string, unknown>) { return api.post<ProductOption>(`/tenants/${tenantId}/products/${productId}/options`, payload) },
  updateOption(tenantId: string, productId: string, id: string, payload: Record<string, unknown>) { return api.put<ProductOption>(`/tenants/${tenantId}/products/${productId}/options/${id}`, payload) },
  deleteOption(tenantId: string, productId: string, id: string) { return api.delete(`/tenants/${tenantId}/products/${productId}/options/${id}`) },
  createOptionValue(tenantId: string, productId: string, optionId: string, payload: Record<string, unknown>) { return api.post<ProductOptionValue>(`/tenants/${tenantId}/products/${productId}/options/${optionId}/values`, payload) },
  updateOptionValue(tenantId: string, productId: string, optionId: string, id: string, payload: Record<string, unknown>) { return api.put<ProductOptionValue>(`/tenants/${tenantId}/products/${productId}/options/${optionId}/values/${id}`, payload) },
  deleteOptionValue(tenantId: string, productId: string, optionId: string, id: string) { return api.delete(`/tenants/${tenantId}/products/${productId}/options/${optionId}/values/${id}`) },
  listVariants(tenantId: string, productId: string) { return api.get<ProductVariant[]>(`/tenants/${tenantId}/products/${productId}/variants`) },
  createVariant(tenantId: string, productId: string, payload: Record<string, unknown>) { return api.post<ProductVariant>(`/tenants/${tenantId}/products/${productId}/variants`, payload) },
  updateVariant(tenantId: string, productId: string, id: string, payload: Record<string, unknown>) { return api.put<ProductVariant>(`/tenants/${tenantId}/products/${productId}/variants/${id}`, payload) },
  deleteVariant(tenantId: string, productId: string, id: string) { return api.delete(`/tenants/${tenantId}/products/${productId}/variants/${id}`) },
  listMedia(tenantId: string, productId: string) { return api.get<ProductMedia[]>(`/tenants/${tenantId}/products/${productId}/media`) },
  createMedia(tenantId: string, productId: string, payload: FormData) { return api.post<ProductMedia>(`/tenants/${tenantId}/products/${productId}/media`, payload) },
  updateMedia(tenantId: string, productId: string, id: string, payload: Record<string, unknown>) { return api.put<ProductMedia>(`/tenants/${tenantId}/products/${productId}/media/${id}`, payload) },
  deleteMedia(tenantId: string, productId: string, id: string) { return api.delete(`/tenants/${tenantId}/products/${productId}/media/${id}`) },
}
