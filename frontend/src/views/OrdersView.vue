<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useAuthStore } from '../stores/auth'
import { assignDelivery, confirmDelivery, getDelivery, getNextOrderStatuses, getOrder, getOrderStatuses, getOrders, issueDeliveryOtp, markCashPaymentPaid, updateOrderStatus, type Delivery, type DeliveryAssign, type DeliveryConfirm, type Order, type OrderStatus } from '../lib/cart'

const auth = useAuthStore()
const orders = ref<Order[]>([])
const statuses = ref<OrderStatus[]>([])
const nextStatuses = ref<OrderStatus[]>([])
const selectedOrder = ref<Order | null>(null)
const selectedStatus = ref('')
const loading = ref(true)
const updating = ref(false)
const markingPayment = ref(false)
const error = ref('')
const actionLoading = ref(false)
const tenantId = computed(() => auth.activeTenant?.public_id || '')

// Delivery management
const delivery = ref<Delivery | null>(null)
const loadingDelivery = ref(false)
const assigningDelivery = ref(false)
const issuingOtp = ref(false)
const confirmingDelivery = ref(false)
const otpInput = ref('')
const deliveryNote = ref('')
const showDeliveryPanel = ref(false)

function money(minor: number, currency: string) { return new Intl.NumberFormat('en-KE', { style: 'currency', currency, maximumFractionDigits: 2 }).format(minor / 100) }
function date(value: string) { return new Intl.DateTimeFormat('en-KE', { dateStyle: 'medium', timeStyle: 'short' }).format(new Date(value)) }
function apiError(err: any, fallback: string) { return err?.response?.data?.detail || fallback }
function statusClass(status: OrderStatus) { return status.is_terminal ? 'commerce-status commerce-status-terminal' : 'commerce-status commerce-status-progress' }

async function load() {
  if (!tenantId.value) return
  loading.value = true; error.value = ''
  try {
    const [ordersResponse, statusesResponse] = await Promise.all([getOrders(tenantId.value, { limit: 100, status_public_id: selectedStatus.value || undefined }), getOrderStatuses(tenantId.value)])
    orders.value = ordersResponse.data; statuses.value = statusesResponse.data
  } catch (err: any) { error.value = apiError(err, 'We could not load your orders.') }
  finally { loading.value = false }
}

async function loadNextStatuses(order: Order) {
  if (!tenantId.value || order.status.is_terminal) { nextStatuses.value = []; return }
  try { nextStatuses.value = (await getNextOrderStatuses(tenantId.value, order.public_id)).data }
  catch (err: any) { nextStatuses.value = []; error.value = apiError(err, 'We could not load the next order actions.') }
}

async function openOrder(order: Order) {
  if (!tenantId.value) return
  try {
    selectedOrder.value = (await getOrder(tenantId.value, order.public_id)).data
    await loadNextStatuses(selectedOrder.value)
    await loadDelivery()
  } catch (err: any) { error.value = apiError(err, 'We could not load that order.') }
}

async function changeStatus(statusId: string) {
  if (!tenantId.value || !selectedOrder.value || !statusId || updating.value) return
  updating.value = true; actionLoading.value = true; error.value = ''
  try {
    selectedOrder.value = (await updateOrderStatus(tenantId.value, selectedOrder.value.public_id, statusId)).data
    const index = orders.value.findIndex(item => item.public_id === selectedOrder.value?.public_id)
    if (index >= 0 && selectedOrder.value) orders.value[index] = selectedOrder.value
    await loadNextStatuses(selectedOrder.value)
  } catch (err: any) { error.value = apiError(err, 'We could not update the order status.') }
  finally { updating.value = false; actionLoading.value = false }
}

async function markPaymentPaid() {
  if (!tenantId.value || !selectedOrder.value?.payment || markingPayment.value) return
  markingPayment.value = true; error.value = ''
  try {
    selectedOrder.value.payment = (await markCashPaymentPaid(tenantId.value, selectedOrder.value.payment.public_id)).data
    const index = orders.value.findIndex(item => item.public_id === selectedOrder.value?.public_id)
    if (index >= 0 && selectedOrder.value) orders.value[index] = selectedOrder.value
  } catch (err: any) { error.value = apiError(err, 'We could not update the payment.') }
  finally { markingPayment.value = false }
}

async function loadDelivery() {
  if (!tenantId.value || !selectedOrder.value) return
  loadingDelivery.value = true; error.value = ''
  try {
    delivery.value = (await getDelivery(tenantId.value, selectedOrder.value.public_id)).data
  } catch (err: any) { error.value = apiError(err, 'We could not load delivery information.') }
  finally { loadingDelivery.value = false }
}

async function assignDeliveryToSelf() {
  if (!tenantId.value || !selectedOrder.value || assigningDelivery.value) return
  assigningDelivery.value = true; error.value = ''
  try {
    // In a real implementation, you'd get the current user's ID from auth store
    // For now, this is a placeholder
    const payload: DeliveryAssign = { assigned_user_id: 1 } // This should be auth.user.id
    delivery.value = (await assignDelivery(tenantId.value, selectedOrder.value.public_id, payload)).data
    showDeliveryPanel.value = true
  } catch (err: any) { error.value = apiError(err, 'We could not assign delivery.') }
  finally { assigningDelivery.value = false }
}

async function issueOtp() {
  if (!tenantId.value || !selectedOrder.value || issuingOtp.value) return
  issuingOtp.value = true; error.value = ''
  try {
    const result = (await issueDeliveryOtp(tenantId.value, selectedOrder.value.public_id)).data
    alert(`Delivery OTP: ${result.otp} (expires at ${new Date(result.expires_at).toLocaleString()})`)
    await loadDelivery()
  } catch (err: any) { error.value = apiError(err, 'We could not issue delivery OTP.') }
  finally { issuingOtp.value = false }
}

async function confirmDeliveryWithOtp() {
  if (!tenantId.value || !selectedOrder.value || confirmingDelivery.value || !otpInput.value.trim()) return
  confirmingDelivery.value = true; error.value = ''
  try {
    const payload: DeliveryConfirm = { otp: otpInput.value.trim(), note: deliveryNote.value.trim() || undefined }
    delivery.value = (await confirmDelivery(tenantId.value, selectedOrder.value.public_id, payload)).data
    otpInput.value = ''; deliveryNote.value = ''
    await loadDelivery()
  } catch (err: any) { error.value = apiError(err, 'We could not confirm delivery.') }
  finally { confirmingDelivery.value = false }
}

onMounted(load)
</script>

<template>
  <section class="page orders-page">
    <div class="page-header">
      <div><span class="page-eyebrow">Commerce</span><h1>Orders</h1><p>Keep track of customer purchases and move each order through your workflow.</p></div>
      <div class="orders-header-actions"><select v-model="selectedStatus" @change="load"><option value="">All orders</option><option v-for="status in statuses" :key="status.public_id" :value="status.public_id">{{ status.name }}</option></select><button class="button button-secondary" type="button" :disabled="loading" @click="load">Refresh</button></div>
    </div>

    <div v-if="error" class="commerce-error">{{ error }}</div>
    <div v-if="loading" class="commerce-state"><div class="status-spinner" /><p>Loading orders…</p></div>
    <div v-else-if="!orders.length" class="commerce-empty"><div class="commerce-empty-icon">✓</div><h2>No orders yet</h2><p>Customer purchases will appear here after checkout.</p></div>
    <div v-else class="orders-layout">
      <div class="orders-list">
        <button v-for="order in orders" :key="order.public_id" type="button" class="order-row" :class="{ active: selectedOrder?.public_id === order.public_id }" @click="openOrder(order)">
          <div class="order-row-main"><strong>#{{ order.order_number }}</strong><span>{{ order.customer_first_name }} {{ order.customer_last_name }}</span><small>{{ date(order.created_at) }}</small></div>
          <div class="order-row-side"><span :class="statusClass(order.status)">{{ order.status.name }}</span><strong>{{ money(order.total_minor, order.currency) }}</strong></div>
        </button>
      </div>

      <aside v-if="selectedOrder" class="order-detail-card">
        <div class="order-detail-head"><div><span class="page-eyebrow">Order</span><h2>#{{ selectedOrder.order_number }}</h2><p>{{ date(selectedOrder.created_at) }}</p></div><button type="button" class="commerce-close" aria-label="Close order" @click="selectedOrder = null">×</button></div>
        <div class="order-customer"><strong>{{ selectedOrder.customer_first_name }} {{ selectedOrder.customer_last_name }}</strong><span>{{ selectedOrder.customer_phone }}</span><span v-if="selectedOrder.customer_email">{{ selectedOrder.customer_email }}</span></div>
        <div class="order-delivery"><div><span>Delivery option</span><strong>{{ selectedOrder.delivery_option === 'pickup' ? 'Pickup from store' : selectedOrder.delivery_option === 'express' ? 'Express delivery' : 'Standard delivery' }}</strong></div><div><span>Address</span><strong>{{ selectedOrder.delivery_address }}</strong></div><div v-if="selectedOrder.delivery_landmark"><span>Landmark</span><strong>{{ selectedOrder.delivery_landmark }}</strong></div><div v-if="selectedOrder.delivery_notes"><span>Delivery notes</span><strong>{{ selectedOrder.delivery_notes }}</strong></div></div>
        
        <div class="order-delivery-management">
          <div class="delivery-header"><span>Delivery</span><button v-if="!showDeliveryPanel" class="button button-secondary button-sm" type="button" @click="showDeliveryPanel = true">Manage</button></div>
          <div v-if="showDeliveryPanel" class="delivery-panel">
            <div v-if="loadingDelivery" class="commerce-state"><div class="status-spinner" /><p>Loading delivery info…</p></div>
            <div v-else-if="delivery">
              <div class="delivery-status"><span>Status</span><strong>{{ delivery.status }}</strong></div>
              <div v-if="delivery.assigned_user_id"><span>Assigned to</span><strong>User ID: {{ delivery.assigned_user_id }}</strong></div>
              <div v-if="delivery.delivered_at"><span>Delivered at</span><strong>{{ date(delivery.delivered_at) }}</strong></div>
              <div v-if="delivery.otp_expires_at"><span>OTP expires</span><strong>{{ date(delivery.otp_expires_at) }}</strong></div>
              <div v-if="delivery.otp_attempts"><span>OTP attempts</span><strong>{{ delivery.otp_attempts }}</strong></div>
              
              <div class="delivery-actions">
                <button v-if="!delivery.assigned_user_id" class="button button-primary button-sm" type="button" :disabled="assigningDelivery" @click="assignDeliveryToSelf">{{ assigningDelivery ? 'Assigning…' : 'Assign to me' }}</button>
                <button v-if="delivery.assigned_user_id && !delivery.delivered_at" class="button button-secondary button-sm" type="button" :disabled="issuingOtp" @click="issueOtp">{{ issuingOtp ? 'Issuing…' : 'Issue OTP' }}</button>
                <button v-if="delivery.assigned_user_id && !delivery.delivered_at" class="button button-secondary button-sm" type="button" @click="showDeliveryPanel = false">Close</button>
              </div>
              
              <div v-if="delivery.assigned_user_id && !delivery.delivered_at" class="otp-confirm">
                <h4>Confirm delivery</h4>
                <div class="form-group"><label>Enter OTP</label><input v-model="otpInput" type="text" placeholder="6-digit code" maxlength="6" /></div>
                <div class="form-group"><label>Delivery note <em>Optional</em></label><textarea v-model="deliveryNote" rows="2" placeholder="Any notes about the delivery" /></div>
                <button class="button button-primary button-sm" type="button" :disabled="confirmingDelivery || !otpInput.trim()" @click="confirmDeliveryWithOtp">{{ confirmingDelivery ? 'Confirming…' : 'Confirm delivery' }}</button>
              </div>
            </div>
            <div v-else class="delivery-empty"><p>No delivery information available. Click "Assign to me" to start delivery process.</p></div>
          </div>
        </div>
        <div v-if="selectedOrder.payment" class="order-payment-panel"><div><span>Payment</span><strong>{{ selectedOrder.payment.method.name }}</strong></div><div><span>Status</span><strong>{{ selectedOrder.payment.status }}</strong></div><button v-if="selectedOrder.payment.method.code === 'cash' && selectedOrder.payment.status === 'pending'" type="button" class="button button-secondary button-block" :disabled="markingPayment" @click="markPaymentPaid">{{ markingPayment ? 'Saving…' : 'Mark cash as paid' }}</button></div>
        <div class="order-items"><div v-for="item in selectedOrder.items" :key="item.public_id" class="order-item-row"><div><strong>{{ item.product_name }}</strong><small v-if="item.variant_label">{{ item.variant_label }}</small><small>{{ item.quantity }} × {{ money(item.unit_price_minor, selectedOrder.currency) }}</small></div><strong>{{ money(item.line_total_minor, selectedOrder.currency) }}</strong></div></div>
        <div v-if="selectedOrder.notes" class="order-note"><span>Customer note</span><p>{{ selectedOrder.notes }}</p></div>
        <div class="order-total"><span>Total</span><strong>{{ money(selectedOrder.total_minor, selectedOrder.currency) }}</strong></div>
        <div v-if="nextStatuses.length" class="order-next-actions"><span>Next step</span><div><button v-for="status in nextStatuses" :key="status.public_id" type="button" class="button button-primary button-block" :disabled="actionLoading" @click="changeStatus(status.public_id)">{{ actionLoading ? 'Updating…' : status.name }}</button></div></div>
        <p v-else class="commerce-muted">{{ selectedOrder.status.is_terminal ? 'This order is in a final status.' : 'No valid next step is configured for this order.' }}</p>
      </aside>
      <aside v-else class="order-detail-placeholder"><div class="commerce-empty-icon">←</div><h2>Select an order</h2><p>Choose an order to see the customer, items and next available action.</p></aside>
    </div>
  </section>
</template>

<style scoped>
.order-delivery { margin-bottom: 1.5rem; padding: 1rem; background: #f9fafb; border-radius: 0.5rem; }
.order-delivery > div { display: flex; justify-content: space-between; padding: 0.5rem 0; border-bottom: 1px solid #e5e7eb; }
.order-delivery > div:last-child { border-bottom: none; }
.order-delivery span { font-size: 0.875rem; color: #6b7280; }
.order-delivery-management { margin-bottom: 1.5rem; }
.delivery-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem; padding-bottom: 0.5rem; border-bottom: 1px solid #e5e7eb; }
.delivery-panel { padding: 1rem; background: #f9fafb; border-radius: 0.5rem; }
.delivery-status, .delivery-panel > div { display: flex; justify-content: space-between; padding: 0.5rem 0; }
.delivery-panel > div { border-bottom: 1px solid #e5e7eb; }
.delivery-panel > div:last-child { border-bottom: none; }
.delivery-panel span { font-size: 0.875rem; color: #6b7280; }
.delivery-actions { display: flex; gap: 0.5rem; margin-top: 1rem; padding-top: 1rem; border-top: 1px solid #e5e7eb; }
.otp-confirm { margin-top: 1rem; padding-top: 1rem; border-top: 1px solid #e5e7eb; }
.otp-confirm h4 { margin-bottom: 0.75rem; font-size: 0.875rem; }
.otp-confirm .form-group { margin-bottom: 0.75rem; }
.otp-confirm .form-group label { display: block; margin-bottom: 0.25rem; font-size: 0.875rem; color: #6b7280; }
.otp-confirm .form-group input, .otp-confirm .form-group textarea { width: 100%; padding: 0.5rem; border: 1px solid #e5e7eb; border-radius: 0.25rem; }
.delivery-empty { text-align: center; padding: 1rem; color: #6b7280; }
.button-sm { padding: 0.375rem 0.75rem; font-size: 0.875rem; }
</style>
