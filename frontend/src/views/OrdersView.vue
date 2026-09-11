<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useAuthStore } from '../stores/auth'
import { getNextOrderStatuses, getOrder, getOrderStatuses, getOrders, markCashPaymentPaid, updateOrderStatus, type Order, type OrderStatus } from '../lib/cart'

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
