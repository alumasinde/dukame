import { api } from './api'

export interface CartItem { public_id: string; product_public_id: string; product_name: string; product_slug: string; variant_public_id: string | null; variant_label: string | null; sku: string | null; image_url: string | null; quantity: number; unit_price_minor: number; line_total_minor: number; currency: string }
export interface Cart { public_id: string; currency: string; items: CartItem[]; item_count: number; subtotal_minor: number }
export interface PaymentMethod { public_id: string; code: string; name: string; payment_type?: 'paybill' | 'till' | 'stk_push' | string | null; instructions?: string | null; is_enabled?: boolean; callback_url?: string | null; callback_token?: string | null }
export interface Payment { public_id: string; status: string; amount_minor: number; currency: string; method: PaymentMethod; failure_reason?: string | null; paid_at?: string | null; provider_reference?: string | null }
export interface PaymentListItem extends Payment { order_public_id: string; order_number: string; customer_first_name: string; customer_last_name: string; customer_phone: string; attempt_count: number; created_at: string }
export interface CheckoutPayload { first_name: string; last_name: string; phone: string; email?: string; delivery_address: string; delivery_landmark?: string; delivery_notes?: string; delivery_option?: string; notes?: string; payment_method_public_id?: string }
export interface PaymentMethodConfig { consumer_key: string; consumer_secret: string; shortcode: string; passkey: string; environment: 'sandbox' | 'production'; transaction_type: 'CustomerPayBillOnline' | 'CustomerBuyGoodsOnline'; account_reference?: string; transaction_desc?: string }
export interface OrderStatus { public_id: string; code: string; name: string; description: string | null; sort_order: number; is_terminal: boolean }
export interface OrderStatusHistory { status: OrderStatus; source: string; created_at: string }
export interface OrderItem { public_id: string; product_public_id: string; variant_public_id: string | null; product_name: string; variant_label: string | null; sku: string | null; quantity: number; unit_price_minor: number; line_total_minor: number }
export interface Order { public_id: string; order_number: string; status: OrderStatus; store_name?: string | null; customer_first_name: string; customer_last_name: string; customer_email: string | null; customer_phone: string; delivery_address: string; delivery_landmark: string | null; delivery_notes: string | null; delivery_option: string; notes: string | null; currency: string; subtotal_minor: number; total_minor: number; items: OrderItem[]; created_at: string; tracking_url?: string | null; payment?: Payment | null }
export interface OrderTracking { store_name: string; order_number: string; status: OrderStatus; status_history: OrderStatusHistory[]; customer_first_name: string; currency: string; subtotal_minor: number; total_minor: number; items: OrderItem[]; created_at: string; updated_at: string; tracking_url: string; payment?: Payment | null; delivery_address?: string | null; delivery_landmark?: string | null; delivery_notes?: string | null; delivery_option?: string | null }

export interface Customer { public_id: string; first_name: string; last_name: string; phone: string; email: string | null; notes: string | null; is_active: boolean; order_count: number }
export interface CustomerCreate { first_name: string; last_name: string; phone: string; email?: string; notes?: string }
export interface CustomerUpdate { first_name?: string; last_name?: string; email?: string; notes?: string; is_active?: boolean }
export interface CustomerOrder { public_id: string; order_number: string; status_public_id: string; status_code: string; status_name: string; currency: string; subtotal_minor: number; total_minor: number; created_at: string }

function path(storeSlug: string, suffix = '') { return `/storefront/${encodeURIComponent(storeSlug)}${suffix}` }
export function getCart(storeSlug: string) { return api.get<Cart>(path(storeSlug, '/cart')) }
export function getPaymentMethods(storeSlug: string) { return api.get<PaymentMethod[]>(path(storeSlug, '/payment-methods')) }
export function addCartItem(storeSlug: string, productPublicId: string, quantity: number, variantPublicId?: string | null) { return api.post<Cart>(path(storeSlug, '/cart/items'), { product_public_id: productPublicId, variant_public_id: variantPublicId || undefined, quantity }) }
export function updateCartItem(storeSlug: string, itemPublicId: string, quantity: number) { return api.patch<Cart>(path(storeSlug, `/cart/items/${encodeURIComponent(itemPublicId)}`), { quantity }) }
export function removeCartItem(storeSlug: string, itemPublicId: string) { return api.delete<Cart>(path(storeSlug, `/cart/items/${encodeURIComponent(itemPublicId)}`)) }
export function checkoutCart(storeSlug: string, payload: CheckoutPayload) { return api.post<Order>(path(storeSlug, '/cart/checkout'), payload) }
export function getOrderTracking(storeSlug: string, token: string) { return api.get<OrderTracking>(path(storeSlug, `/order/track/${encodeURIComponent(token)}`)) }
/** Public order lookup by order number + phone (no tracking token). Returns tracking payload including tracking_url. */
export function lookupOrder(storeSlug: string, payload: { order_number: string; phone: string }) {
  return api.post<OrderTracking>(path(storeSlug, '/order/lookup'), payload)
}
/** Customer-facing STK retry using the order tracking token (no merchant auth). */
export function retryStorefrontPayment(storeSlug: string, trackingToken: string) {
  return api.post<Payment>(path(storeSlug, `/order/track/${encodeURIComponent(trackingToken)}/payment/retry`))
}
export function getPaymentMethodsForTenant(tenantPublicId: string) { return api.get<PaymentMethod[]>(`/tenants/${encodeURIComponent(tenantPublicId)}/payment-methods`) }
export function createPaymentMethod(tenantPublicId: string, payload: { code: string; name: string; instructions?: string; is_enabled?: boolean; config?: Record<string, string> }) { return api.post<PaymentMethod>(`/tenants/${encodeURIComponent(tenantPublicId)}/payment-methods`, payload) }
export function updatePaymentMethod(tenantPublicId: string, methodPublicId: string, payload: { name?: string; instructions?: string; is_enabled?: boolean; config?: Record<string, string> }) { return api.patch<PaymentMethod>(`/tenants/${encodeURIComponent(tenantPublicId)}/payment-methods/${encodeURIComponent(methodPublicId)}`, payload) }
export function testPaymentMethod(tenantPublicId: string, methodPublicId: string) { return api.post<{ status: string; message: string }>(`/tenants/${encodeURIComponent(tenantPublicId)}/payment-methods/${encodeURIComponent(methodPublicId)}/test`) }
export function getPayments(tenantPublicId: string, params?: { offset?: number; limit?: number; status?: string }) { return api.get<PaymentListItem[]>(`/tenants/${encodeURIComponent(tenantPublicId)}/payments`, { params }) }
export function getPayment(tenantPublicId: string, paymentPublicId: string) { return api.get<PaymentListItem>(`/tenants/${encodeURIComponent(tenantPublicId)}/payments/${encodeURIComponent(paymentPublicId)}`) }
export function retryPayment(tenantPublicId: string, paymentPublicId: string) { return api.post<Payment>(`/tenants/${encodeURIComponent(tenantPublicId)}/payments/${encodeURIComponent(paymentPublicId)}/retry`) }
export function getOrderStatuses(tenantPublicId: string) { return api.get<OrderStatus[]>(`/tenants/${encodeURIComponent(tenantPublicId)}/orders/statuses`) }
export function getOrders(tenantPublicId: string, params?: { offset?: number; limit?: number; status_public_id?: string }) { return api.get<Order[]>(`/tenants/${encodeURIComponent(tenantPublicId)}/orders`, { params }) }
export function getOrder(tenantPublicId: string, orderPublicId: string) { return api.get<Order>(`/tenants/${encodeURIComponent(tenantPublicId)}/orders/${encodeURIComponent(orderPublicId)}`) }
export function getNextOrderStatuses(tenantPublicId: string, orderPublicId: string) { return api.get<OrderStatus[]>(`/tenants/${encodeURIComponent(tenantPublicId)}/orders/${encodeURIComponent(orderPublicId)}/next-statuses`) }
export function updateOrderStatus(tenantPublicId: string, orderPublicId: string, statusPublicId: string) { return api.patch<Order>(`/tenants/${encodeURIComponent(tenantPublicId)}/orders/${encodeURIComponent(orderPublicId)}/status`, { status_public_id: statusPublicId }) }
export function markCashPaymentPaid(tenantPublicId: string, paymentPublicId: string) { return api.patch<Payment>(`/tenants/${encodeURIComponent(tenantPublicId)}/payments/${encodeURIComponent(paymentPublicId)}/cash-paid`) }
export function markManualPaymentPaid(tenantPublicId: string, paymentPublicId: string) { return api.patch<Payment>(`/tenants/${encodeURIComponent(tenantPublicId)}/payments/${encodeURIComponent(paymentPublicId)}/manual-paid`) }
export function getCustomers(tenantPublicId: string, params?: { offset?: number; limit?: number; search?: string }) { return api.get<Customer[]>(`/tenants/${encodeURIComponent(tenantPublicId)}/customers`, { params }) }
export function createCustomer(tenantPublicId: string, payload: CustomerCreate) { return api.post<Customer>(`/tenants/${encodeURIComponent(tenantPublicId)}/customers`, payload) }
export function getCustomer(tenantPublicId: string, customerPublicId: string) { return api.get<Customer>(`/tenants/${encodeURIComponent(tenantPublicId)}/customers/${encodeURIComponent(customerPublicId)}`) }
export function updateCustomer(tenantPublicId: string, customerPublicId: string, payload: CustomerUpdate) { return api.put<Customer>(`/tenants/${encodeURIComponent(tenantPublicId)}/customers/${encodeURIComponent(customerPublicId)}`, payload) }
export function getCustomerOrders(tenantPublicId: string, customerPublicId: string, params?: { offset?: number; limit?: number }) { return api.get<CustomerOrder[]>(`/tenants/${encodeURIComponent(tenantPublicId)}/customers/${encodeURIComponent(customerPublicId)}/orders`, { params }) }

export interface Delivery { public_id: string; order_public_id: string; order_number: string; status: string; assigned_user_id: number | null; delivered_at: string | null; delivered_by_user_id: number | null; delivery_note: string | null; otp_expires_at: string | null; otp_verified_at: string | null; otp_attempts: number; created_at: string; updated_at: string }
export interface DeliveryAssign { assigned_user_id: number }
export interface DeliveryConfirm { otp: string; note?: string }
export interface DeliveryOtp { delivery_public_id: string; expires_at: string; otp: string }

export function getDelivery(tenantPublicId: string, orderPublicId: string) { return api.get<Delivery>(`/tenants/${encodeURIComponent(tenantPublicId)}/orders/${encodeURIComponent(orderPublicId)}/delivery`) }
export function assignDelivery(tenantPublicId: string, orderPublicId: string, payload: DeliveryAssign) { return api.post<Delivery>(`/tenants/${encodeURIComponent(tenantPublicId)}/orders/${encodeURIComponent(orderPublicId)}/delivery/assign`, payload) }
export function issueDeliveryOtp(tenantPublicId: string, orderPublicId: string) { return api.post<DeliveryOtp>(`/tenants/${encodeURIComponent(tenantPublicId)}/orders/${encodeURIComponent(orderPublicId)}/delivery/otp`) }
export function confirmDelivery(tenantPublicId: string, orderPublicId: string, payload: DeliveryConfirm) { return api.post<Delivery>(`/tenants/${encodeURIComponent(tenantPublicId)}/orders/${encodeURIComponent(orderPublicId)}/delivery/confirm`, payload) }

export interface Role { public_id: string; name: string; slug: string; is_system: boolean; permissions: string[] }
export interface Permission { key: string; name: string }
export interface RoleCreate { name: string; slug: string; permissions: string[] }
export interface RolePermissionsUpdate { permissions: string[] }

export function getRoles(tenantPublicId: string) { return api.get<Role[]>(`/tenants/${encodeURIComponent(tenantPublicId)}/roles`) }
export function getPermissions(tenantPublicId: string) { return api.get<Permission[]>(`/tenants/${encodeURIComponent(tenantPublicId)}/roles/permissions`) }
export function createRole(tenantPublicId: string, payload: RoleCreate) { return api.post<Role>(`/tenants/${encodeURIComponent(tenantPublicId)}/roles`, payload) }
export function updateRolePermissions(tenantPublicId: string, rolePublicId: string, payload: RolePermissionsUpdate) { return api.put<Role>(`/tenants/${encodeURIComponent(tenantPublicId)}/roles/${encodeURIComponent(rolePublicId)}/permissions`, payload) }
