<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { RouterLink, useRoute } from 'vue-router'
import { getOrderTracking, type OrderTracking } from '../lib/cart'

const route = useRoute()
const storeSlug = String(route.params.storeSlug)
const token = String(route.params.trackingToken)
const order = ref<OrderTracking | null>(null)
const loading = ref(true)
const refreshing = ref(false)
const error = ref('')
let timer: ReturnType<typeof setInterval> | undefined

const terminal = computed(() => order.value?.status.is_terminal ?? false)
const lastUpdated = computed(() => order.value ? new Intl.DateTimeFormat('en-KE', { dateStyle: 'medium', timeStyle: 'short' }).format(new Date(order.value.updated_at)) : '')

function money(minor: number, currency: string) {
  return new Intl.NumberFormat('en-KE', { style: 'currency', currency, maximumFractionDigits: 2 }).format(minor / 100)
}

function date(value: string) {
  return new Intl.DateTimeFormat('en-KE', { dateStyle: 'medium', timeStyle: 'short' }).format(new Date(value))
}

function isCurrent(statusId: string) { return order.value?.status.public_id === statusId }

async function load(initial = false) {
  if (initial) loading.value = true
  else refreshing.value = true
  try {
    order.value = (await getOrderTracking(storeSlug, token)).data
    error.value = ''
  } catch (err: any) {
    if (initial) error.value = err?.response?.data?.detail || 'We could not find this order.'
  } finally {
    loading.value = false
    refreshing.value = false
  }
}

onMounted(async () => {
  await load(true)
  timer = setInterval(() => {
    if (!terminal.value) void load()
  }, 5000)
})

onBeforeUnmount(() => {
  if (timer) clearInterval(timer)
})
</script>

<template>
  <main class="order-tracking-page">
    <header class="order-tracking-header">
      <RouterLink :to="`/${storeSlug}`" class="storefront-brand storefront-brand-link">
        <span class="storefront-mark">D</span>
        <div><strong>{{ order?.store_name || 'Store' }}</strong><small>Powered by DukaMe</small></div>
      </RouterLink>
      <RouterLink :to="`/${storeSlug}`" class="order-tracking-shop">Continue shopping</RouterLink>
    </header>

    <section v-if="loading" class="order-tracking-state"><div class="status-spinner" /><p>Loading your order…</p></section>

    <section v-else-if="error" class="order-tracking-state order-tracking-error"><div class="order-tracking-state-icon">!</div><h1>Order not found</h1><p>{{ error }}</p><RouterLink :to="`/${storeSlug}`" class="button button-primary">Back to store</RouterLink></section>

    <section v-else-if="order" class="order-tracking-shell">
      <div class="order-tracking-heading">
        <div><span class="storefront-eyebrow">Order tracking</span><h1>Order #{{ order.order_number }}</h1><p>Hi {{ order.customer_first_name }}, your order is being updated automatically.</p></div>
        <span class="order-live" :class="{ complete: terminal }"><span />{{ refreshing ? 'Updating…' : terminal ? 'Order complete' : 'Live updates' }}</span>
      </div>

      <div class="order-tracking-grid">
        <section class="order-progress-card">
          <div class="order-progress-head"><div><strong>{{ order.status.name }}</strong><span>{{ order.status.description || 'Your order is moving through the store workflow.' }}</span></div><small>Updated {{ lastUpdated }}</small></div>
          <div class="order-progress-list" aria-label="Order progress">
            <article v-for="(event, index) in order.status_history" :key="`${event.status.public_id}-${event.created_at}`" class="order-progress-step" :class="{ current: isCurrent(event.status.public_id), done: !isCurrent(event.status.public_id) && index < order.status_history.length - 1 }">
              <div class="order-progress-marker"><span v-if="!isCurrent(event.status.public_id)">✓</span><span v-else /> </div>
              <div class="order-progress-copy"><strong>{{ event.status.name }}</strong><p>{{ event.status.description }}</p><small>{{ date(event.created_at) }}</small></div>
            </article>
          </div>
          <div v-if="!terminal" class="order-progress-wait"><span class="order-pulse" /> The store will update your order as it moves to the next step.</div>
          <div v-else class="order-progress-wait complete"><span>✓</span> Your order has reached a final status.</div>
        </section>

        <aside class="order-summary-card">
          <div class="order-summary-head"><strong>Your order</strong><span>{{ order.items.reduce((sum, item) => sum + item.quantity, 0) }} items</span></div>
          <div class="order-summary-items">
            <div v-for="item in order.items" :key="item.public_id" class="order-summary-item"><div><strong>{{ item.product_name }}</strong><small v-if="item.variant_label">{{ item.variant_label }}</small><small>{{ item.quantity }} × {{ money(item.unit_price_minor, order.currency) }}</small></div><strong>{{ money(item.line_total_minor, order.currency) }}</strong></div>
          </div>
          <div class="order-summary-total"><span>Total</span><strong>{{ money(order.total_minor, order.currency) }}</strong></div>
          <p class="order-summary-note">Updates are sent to your phone when the store changes your order status.</p>
          <a v-if="order.tracking_url" :href="order.tracking_url" class="order-copy-link">Tracking link</a>
          <RouterLink :to="`/${storeSlug}`" class="button button-secondary button-block">Continue shopping</RouterLink>
        </aside>
      </div>
    </section>
  </main>
</template>
