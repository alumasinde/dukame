import { api } from './api'

export interface CartItem {
  public_id: string
  product_public_id: string
  product_name: string
  product_slug: string
  variant_public_id: string | null
  variant_label: string | null
  sku: string | null
  image_url: string | null
  quantity: number
  unit_price_minor: number
  line_total_minor: number
  currency: string
}

export interface Cart {
  public_id: string
  currency: string
  items: CartItem[]
  item_count: number
  subtotal_minor: number
}

export interface CheckoutPayload {
  first_name: string
  last_name: string
  phone: string
  email?: string
  notes?: string
}

export interface OrderStatus {
  public_id: string
  code: string
  name: string
  description: string | null
  sort_order: number
  is_terminal: boolean
}

export interface OrderItem {
  public_id: string
  product_public_id: string
  variant_public_id: string | null
  product_name: string
  variant_label: string | null
  sku: string | null
  quantity: number
  unit_price_minor: number
  line_total_minor: number
}

export interface Order {
  public_id: string
  order_number: string
  status: OrderStatus
  customer_first_name: string
  customer_last_name: string
  customer_email: string | null
  customer_phone: string
  notes: string | null
  currency: string
  subtotal_minor: number
  total_minor: number
  items: OrderItem[]
  created_at: string
}

function path(storeSlug: string, suffix = '') {
  return `/storefront/${encodeURIComponent(storeSlug)}${suffix}`
}

export function getCart(storeSlug: string) {
  return api.get<Cart>(path(storeSlug, '/cart'))
}

export function addCartItem(storeSlug: string, productPublicId: string, quantity: number, variantPublicId?: string | null) {
  return api.post<Cart>(path(storeSlug, '/cart/items'), {
    product_public_id: productPublicId,
    variant_public_id: variantPublicId || undefined,
    quantity,
  })
}

export function updateCartItem(storeSlug: string, itemPublicId: string, quantity: number) {
  return api.patch<Cart>(path(storeSlug, `/cart/items/${encodeURIComponent(itemPublicId)}`), { quantity })
}

export function removeCartItem(storeSlug: string, itemPublicId: string) {
  return api.delete<Cart>(path(storeSlug, `/cart/items/${encodeURIComponent(itemPublicId)}`))
}

export function checkoutCart(storeSlug: string, payload: CheckoutPayload) {
  return api.post<Order>(path(storeSlug, '/cart/checkout'), payload)
}

export function getOrderStatuses(tenantPublicId: string) {
  return api.get<OrderStatus[]>(`/tenants/${encodeURIComponent(tenantPublicId)}/orders/statuses`)
}

export function getOrders(tenantPublicId: string, params?: { offset?: number; limit?: number; status_public_id?: string }) {
  return api.get<Order[]>(`/tenants/${encodeURIComponent(tenantPublicId)}/orders`, { params })
}

export function getOrder(tenantPublicId: string, orderPublicId: string) {
  return api.get<Order>(`/tenants/${encodeURIComponent(tenantPublicId)}/orders/${encodeURIComponent(orderPublicId)}`)
}

export function updateOrderStatus(tenantPublicId: string, orderPublicId: string, statusPublicId: string) {
  return api.patch<Order>(`/tenants/${encodeURIComponent(tenantPublicId)}/orders/${encodeURIComponent(orderPublicId)}/status`, {
    status_public_id: statusPublicId,
  })
}
