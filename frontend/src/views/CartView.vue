<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { RouterLink, useRoute } from 'vue-router'
import { checkoutCart, removeCartItem, updateCartItem, type Cart, type Order } from '../lib/cart'
import { useCartState } from '../lib/cart-state'

const route = useRoute()
const storeSlug = String(route.params.storeSlug)
const cartState = useCartState()
const cart = ref<Cart | null>(cartState.cart.value)
const order = ref<Order | null>(null)
const loading = ref(!cart.value)
const submitting = ref(false)
const busyItems = ref<Record<string, boolean>>({})
const error = ref('')
const fieldError = ref('')
const form = reactive({ first_name: '', last_name: '', phone: '', email: '', notes: '' })

const itemCountLabel = computed(() => {
  const count = cart.value?.item_count || 0
  return `${count} ${count === 1 ? 'item' : 'items'}`
})

const trackingPath = computed(() => {
  if (!order.value?.tracking_url) return ''
  try { return new URL(order.value.tracking_url, window.location.origin).pathname } catch { return '' }
})

function money(minor: number, currency: string) { return new Intl.NumberFormat('en-KE', { style: 'currency', currency, maximumFractionDigits: 2 }).format(minor / 100) }
function apiError(err: any, fallback: string) { return err?.response?.data?.detail || fallback }
function setBusy(itemId: string, value: boolean) { busyItems.value = { ...busyItems.value, [itemId]: value } }
function recalculate(next: Cart): Cart { next.item_count = next.items.reduce((sum, item) => sum + item.quantity, 0); next.subtotal_minor = next.items.reduce((sum, item) => sum + item.line_total_minor, 0); return next }

async function reconcileCart() {
  try { cart.value = await cartState.load(storeSlug, true) } catch (err: any) { if (!cart.value) error.value = apiError(err, 'We could not load your cart.') } finally { loading.value = false }
}

async function changeQuantity(itemId: string, quantity: number) {
  const current = cart.value
  const item = current?.items.find(entry => entry.public_id === itemId)
  if (!current || !item || quantity < 1 || busyItems.value[itemId]) return
  const previous = current
  const optimistic = recalculate({ ...current, items: current.items.map(entry => entry.public_id === itemId ? { ...entry, quantity, line_total_minor: entry.unit_price_minor * quantity } : entry) })
  cart.value = optimistic; cartState.update(storeSlug, optimistic); setBusy(itemId, true); error.value = ''
  try { const response = await updateCartItem(storeSlug, itemId, quantity); cart.value = response.data; cartState.update(storeSlug, response.data) }
  catch (err: any) { cart.value = previous; cartState.update(storeSlug, previous); error.value = apiError(err, 'We could not update that item.') }
  finally { setBusy(itemId, false) }
}

async function remove(itemId: string) {
  const current = cart.value
  if (!current || busyItems.value[itemId]) return
  const previous = current
  const optimistic = recalculate({ ...current, items: current.items.filter(item => item.public_id !== itemId) })
  cart.value = optimistic; cartState.update(storeSlug, optimistic); setBusy(itemId, true); error.value = ''
  try { const response = await removeCartItem(storeSlug, itemId); cart.value = response.data; cartState.update(storeSlug, response.data) }
  catch (err: any) { cart.value = previous; cartState.update(storeSlug, previous); error.value = apiError(err, 'We could not remove that item.') }
  finally { setBusy(itemId, false) }
}

async function submitOrder() {
  if (!cart.value?.items.length || submitting.value) return
  fieldError.value = ''; error.value = ''
  if (!form.first_name.trim() || !form.last_name.trim() || !form.phone.trim()) { fieldError.value = 'Enter your first name, last name and phone number to continue.'; return }
  submitting.value = true
  try {
    order.value = (await checkoutCart(storeSlug, { first_name: form.first_name.trim(), last_name: form.last_name.trim(), phone: form.phone.trim(), email: form.email.trim() || undefined, notes: form.notes.trim() || undefined })).data
    cart.value = null; cartState.clear(storeSlug)
  } catch (err: any) { error.value = apiError(err, 'We could not place your order. Please try again.'); await reconcileCart() }
  finally { submitting.value = false }
}

onMounted(() => reconcileCart())
</script>

<template>
  <main class="storefront-page">
    <header class="storefront-header">
      <RouterLink :to="`/${storeSlug}`" class="storefront-brand storefront-brand-link"><span class="storefront-mark">D</span><div><strong>Store</strong><small>Powered by DukaMe</small></div></RouterLink>
      <RouterLink :to="`/${storeSlug}`" class="storefront-cart storefront-cart-link">Continue shopping</RouterLink>
    </header>

    <section class="storefront-cart-page">
      <div v-if="loading" class="storefront-state"><div class="status-spinner" /><p>Loading your cart…</p></div>
      <div v-else-if="order" class="storefront-order-success">
        <div class="storefront-success-icon">✓</div><span class="storefront-eyebrow">Order received</span><h1>Thank you, {{ order.customer_first_name }}.</h1><p>Your order <strong>#{{ order.order_number }}</strong> has been received. We'll keep you updated as the store processes it.</p>
        <div class="storefront-success-summary"><div><span>Status</span><strong>{{ order.status.name }}</strong></div><div><span>Total</span><strong>{{ money(order.total_minor, order.currency) }}</strong></div><div><span>Items</span><strong>{{ order.items.reduce((sum, item) => sum + item.quantity, 0) }}</strong></div></div>
        <div class="storefront-success-actions"><RouterLink v-if="trackingPath" :to="trackingPath" class="button button-primary button-lg">Track my order</RouterLink><RouterLink :to="`/${storeSlug}`" class="button button-secondary">Continue shopping</RouterLink></div>
        <p class="storefront-success-notice">Your tracking link was also sent to your phone when SMS notifications are enabled.</p>
      </div>
      <template v-else-if="cart">
        <div class="storefront-cart-heading"><div><RouterLink :to="`/${storeSlug}`" class="storefront-back">← Continue shopping</RouterLink><h1>Your cart</h1><p>{{ itemCountLabel }}</p></div><div v-if="cart.items.length" class="storefront-cart-heading-total"><span>Subtotal</span><strong>{{ money(cart.subtotal_minor, cart.currency) }}</strong></div></div>
        <div v-if="error" class="storefront-inline-error" role="alert">{{ error }}</div>
        <div v-if="cart.items.length" class="storefront-cart-layout">
          <section class="storefront-cart-items" aria-label="Cart items">
            <article v-for="item in cart.items" :key="item.public_id" class="storefront-cart-item" :class="{ 'is-busy': busyItems[item.public_id] }">
              <RouterLink :to="`/${storeSlug}/products/${item.product_slug}`" class="storefront-cart-item-image"><img v-if="item.image_url" :src="item.image_url" :alt="item.product_name" /><span v-else>No image</span></RouterLink>
              <div class="storefront-cart-item-copy"><div class="storefront-cart-item-title"><RouterLink :to="`/${storeSlug}/products/${item.product_slug}`"><strong>{{ item.product_name }}</strong></RouterLink><button type="button" class="storefront-remove" :disabled="busyItems[item.public_id]" @click="remove(item.public_id)">Remove</button></div><small v-if="item.variant_label">{{ item.variant_label }}</small><small v-if="item.sku" class="storefront-item-sku">SKU: {{ item.sku }}</small><div class="storefront-cart-item-bottom"><div class="storefront-quantity" :class="{ disabled: busyItems[item.public_id] }"><button type="button" aria-label="Decrease quantity" :disabled="item.quantity <= 1 || busyItems[item.public_id]" @click="changeQuantity(item.public_id, item.quantity - 1)">−</button><span aria-live="polite">{{ item.quantity }}</span><button type="button" aria-label="Increase quantity" :disabled="busyItems[item.public_id]" @click="changeQuantity(item.public_id, item.quantity + 1)">+</button></div><div class="storefront-cart-item-price"><span>{{ money(item.unit_price_minor, item.currency) }} each</span><strong>{{ money(item.line_total_minor, item.currency) }}</strong></div></div></div>
            </article>
          </section>
          <aside class="storefront-checkout-card"><div class="storefront-checkout-title"><strong>Checkout</strong><span>{{ itemCountLabel }}</span></div><div class="storefront-order-total"><span>Subtotal</span><strong>{{ money(cart.subtotal_minor, cart.currency) }}</strong></div><p class="storefront-checkout-note">Delivery and payment details will be confirmed by the store.</p><div class="storefront-form-grid"><label><span>First name</span><input v-model="form.first_name" autocomplete="given-name" /></label><label><span>Last name</span><input v-model="form.last_name" autocomplete="family-name" /></label><label><span>Phone</span><input v-model="form.phone" type="tel" autocomplete="tel" placeholder="07xx xxx xxx" /></label><label><span>Email <em>Optional</em></span><input v-model="form.email" type="email" autocomplete="email" /></label><label class="storefront-form-full"><span>Order note <em>Optional</em></span><textarea v-model="form.notes" rows="3" placeholder="Anything the store should know?"></textarea></label></div><p v-if="fieldError" class="storefront-form-error">{{ fieldError }}</p><button class="button button-primary button-lg storefront-add" type="button" :disabled="submitting" @click="submitOrder">{{ submitting ? 'Placing order…' : 'Place order' }}</button></aside>
        </div>
        <div v-else class="storefront-empty storefront-cart-empty"><div class="storefront-empty-icon" aria-hidden="true">—</div><h2>Your cart is empty</h2><p>Add a product to your cart and it will appear here.</p><RouterLink :to="`/${storeSlug}`" class="button button-primary">Browse products</RouterLink></div>
      </template>
    </section>
  </main>
</template>
