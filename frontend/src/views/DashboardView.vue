<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { RouterLink } from 'vue-router'
import { getOrders, getPayments, type Order, type PaymentListItem } from '../lib/cart'
import { useAuthStore } from '../stores/auth'

const auth = useAuthStore()
const loading = ref(true)
const error = ref('')
const orders = ref<Order[]>([])
const payments = ref<PaymentListItem[]>([])
const tenant = computed(() => auth.activeTenant)
const firstName = computed(() => auth.user?.first_name || 'there')
const currency = computed(() => payments.value[0]?.currency || orders.value[0]?.currency || 'KES')
const paidPayments = computed(() => payments.value.filter(p => p.status === 'paid'))
const revenueMinor = computed(() => paidPayments.value.reduce((sum, p) => sum + p.amount_minor, 0))
const pendingPayments = computed(() => payments.value.filter(p => ['pending', 'processing'].includes(p.status)).length)
const averageOrderMinor = computed(() => paidPayments.value.length ? Math.round(revenueMinor.value / paidPayments.value.length) : 0)
const pendingOrders = computed(() => orders.value.filter(o => !o.status.is_terminal).length)
const recentOrders = computed(() => orders.value.slice(0, 7))
const paymentMix = computed(() => {
  const map = new Map<string, { name: string; count: number; amount: number }>()
  for (const payment of payments.value) {
    const current = map.get(payment.method.code) || { name: payment.method.name, count: 0, amount: 0 }
    current.count += 1
    if (payment.status === 'paid') current.amount += payment.amount_minor
    map.set(payment.method.code, current)
  }
  return [...map.values()].sort((a, b) => b.amount - a.amount)
})
function money(minor: number) { return new Intl.NumberFormat('en-KE', { style: 'currency', currency: currency.value, maximumFractionDigits: 0 }).format((minor || 0) / 100) }
function statusClass(status: string) { return `status-${status}` }
async function load() {
  if (!tenant.value) { loading.value = false; return }
  loading.value = true; error.value = ''
  try {
    const [ordersResponse, paymentsResponse] = await Promise.all([getOrders(tenant.value.public_id, { limit: 100 }), getPayments(tenant.value.public_id, { limit: 100 })])
    orders.value = ordersResponse.data
    payments.value = paymentsResponse.data
  } catch (err: any) { error.value = err?.response?.data?.detail || 'Dashboard data could not be loaded.' }
  finally { loading.value = false }
}
onMounted(load)
</script>

<template>
  <div class="page-stack">
    <template v-if="tenant">
      <div class="welcome-row">
        <div><span class="eyebrow">Store overview</span><h2>Good day, {{ firstName }}.</h2><p class="lead">A live view of sales, orders and payments for {{ tenant.name }}.</p></div>
        <div style="display:flex;gap:8px"><RouterLink to="/payments" class="button button-secondary">Payments</RouterLink><RouterLink to="/catalogue/products/new" class="button button-primary">+ Add product</RouterLink></div>
      </div>
      <div v-if="error" class="alert alert-warning">{{ error }}</div>
      <div v-if="loading" class="commerce-state"><div class="status-spinner" /><p>Loading your store performance…</p></div>
      <template v-else>
        <div class="stat-grid">
          <div class="stat-card accent-stat"><span class="stat-label">Paid revenue</span><strong>{{ money(revenueMinor) }}</strong><span class="stat-note">From {{ paidPayments.length }} paid payment{{ paidPayments.length === 1 ? '' : 's' }}</span></div>
          <div class="stat-card"><span class="stat-label">Orders</span><strong>{{ orders.length }}</strong><span class="stat-note">{{ pendingOrders }} active</span></div>
          <div class="stat-card"><span class="stat-label">Average order</span><strong>{{ money(averageOrderMinor) }}</strong><span class="stat-note">Based on paid payments</span></div>
          <div class="stat-card"><span class="stat-label">Awaiting payment</span><strong>{{ pendingPayments }}</strong><span class="stat-note">Pending or processing</span></div>
        </div>

        <div class="dashboard-grid">
          <section class="panel panel-large">
            <div class="panel-heading"><div><span class="eyebrow">Sales activity</span><h3>Recent orders</h3><p>Your latest store activity.</p></div><RouterLink to="/orders">View all →</RouterLink></div>
            <div v-if="!recentOrders.length" class="commerce-state"><p>No orders yet. Add products and start selling.</p></div>
            <div v-else class="dashboard-order-list">
              <RouterLink v-for="order in recentOrders" :key="order.public_id" :to="`/orders`" class="dashboard-order-row">
                <span class="dashboard-order-icon"><i class="fa-solid fa-receipt" aria-hidden="true"></i></span>
                <span class="dashboard-order-main"><strong>#{{ order.order_number }}</strong><small>{{ order.customer_first_name }} {{ order.customer_last_name }} · {{ order.items.reduce((sum, item) => sum + item.quantity, 0) }} item{{ order.items.reduce((sum, item) => sum + item.quantity, 0) === 1 ? '' : 's' }}</small></span>
                <span class="dashboard-order-total">{{ money(order.total_minor) }}</span>
                <span class="dashboard-order-status" :class="statusClass(order.status.code)">{{ order.status.name }}</span>
              </RouterLink>
            </div>
          </section>

          <section class="panel">
            <div class="panel-heading"><div><span class="eyebrow">Payments</span><h3>Payment mix</h3><p>How customers are paying.</p></div><RouterLink to="/payments">Manage →</RouterLink></div>
            <div v-if="!paymentMix.length" class="commerce-state"><p>No payment activity yet.</p></div>
            <div v-else class="dashboard-payment-list">
              <div v-for="item in paymentMix" :key="item.name" class="dashboard-payment-row"><span class="dashboard-payment-icon"><i class="fa-solid fa-credit-card" aria-hidden="true"></i></span><div><strong>{{ item.name }}</strong><small>{{ item.count }} transaction{{ item.count === 1 ? '' : 's' }}</small></div><b>{{ money(item.amount) }}</b></div>
            </div>
          </section>
        </div>

        <div class="dashboard-grid">
          <section class="panel">
            <div class="panel-heading"><div><span class="eyebrow">Run your store</span><h3>Quick actions</h3></div></div>
            <div class="quick-actions">
              <RouterLink to="/catalogue/products/new" class="quick-action"><b><i class="fa-solid fa-box" aria-hidden="true"></i></b><span><strong>Add product</strong><small>Grow your catalogue</small></span></RouterLink>
              <RouterLink to="/orders" class="quick-action"><b><i class="fa-solid fa-receipt" aria-hidden="true"></i></b><span><strong>Manage orders</strong><small>Process customer orders</small></span></RouterLink>
              <RouterLink to="/payments" class="quick-action"><b><i class="fa-solid fa-credit-card" aria-hidden="true"></i></b><span><strong>Review payments</strong><small>Check payment status</small></span></RouterLink>
              <RouterLink to="/settings" class="quick-action"><b><i class="fa-solid fa-gear" aria-hidden="true"></i></b><span><strong>Store settings</strong><small>Configure your workspace</small></span></RouterLink>
            </div>
          </section>
          <section class="panel">
            <div class="panel-heading"><div><span class="eyebrow">Store health</span><h3>Next actions</h3></div></div>
            <div class="steps">
              <div class="step"><span>1</span><div><strong>Keep your catalogue current</strong><small>Prices, stock and product information drive checkout accuracy.</small></div><RouterLink to="/catalogue/products">Products →</RouterLink></div>
              <div class="step"><span>2</span><div><strong>Configure payments</strong><small>Enable the payment methods your customers can use.</small></div><RouterLink to="/settings">Settings →</RouterLink></div>
              <div class="step"><span>3</span><div><strong>Process new orders</strong><small>Move orders through your configured workflow.</small></div><RouterLink to="/orders">Orders →</RouterLink></div>
            </div>
          </section>
        </div>
      </template>
    </template>
    <section v-else class="empty-state"><h3>Create your first business</h3><p>Set up your business to start managing products, orders and payments.</p><RouterLink to="/shops" class="button button-primary">Create business</RouterLink></section>
  </div>
</template>
