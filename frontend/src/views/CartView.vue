<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { RouterLink, useRoute } from 'vue-router'
import { checkoutCart, getCart, removeCartItem, updateCartItem, type Cart, type Order } from '../lib/cart'

const route = useRoute()
const storeSlug = String(route.params.storeSlug)
const cart = ref<Cart | null>(null)
const order = ref<Order | null>(null)
const loading = ref(true)
const submitting = ref(false)
const error = ref('')
const fieldError = ref('')
const form = reactive({ first_name: '', last_name: '', phone: '', email: '', notes: '' })

const itemCountLabel = computed(() => {
  const count = cart.value?.item_count || 0
  return `${count} item${count === 1 ? '' : 's'}`
})

function money(minor: number, currency: string) {
  return new Intl.NumberFormat('en-KE', { style: 'currency', currency, maximumFractionDigits: 2 }).format(minor / 100)
}

function apiError(err: any, fallback: string) {
  return err?.response?.data?.detail || fallback
}

async function load() {
  loading.value = true
  error.value = ''
  try {
    cart.value = (await getCart(storeSlug)).data
  } catch (err: any) {
    error.value = apiError(err, 'We could not load your cart.')
  } finally {
    loading.value = false
  }
}

async function changeQuantity(itemId: string, quantity: number) {
  if (!cart.value || quantity < 1) return
  error.value = ''
  try {
    cart.value = (await updateCartItem(storeSlug, itemId, quantity)).data
  } catch (err: any) {
    error.value = apiError(err, 'We could not update that item.')
  }
}

async function remove(itemId: string) {
  if (!cart.value) return
  error.value = ''
  try {
    cart.value = (await removeCartItem(storeSlug, itemId)).data
  } catch (err: any) {
    error.value = apiError(err, 'We could not remove that item.')
  }
}

async function submitOrder() {
  if (!cart.value?.items.length) return
  fieldError.value = ''
  error.value = ''
  if (!form.first_name.trim() || !form.last_name.trim() || !form.phone.trim()) {
    fieldError.value = 'Please enter your first name, last name and phone number.'
    return
  }
  submitting.value = true
  try {
    order.value = (await checkoutCart(storeSlug, {
      first_name: form.first_name.trim(),
      last_name: form.last_name.trim(),
      phone: form.phone.trim(),
      email: form.email.trim() || undefined,
      notes: form.notes.trim() || undefined,
    })).data
    cart.value = null
  } catch (err: any) {
    error.value = apiError(err, 'We could not place your order. Please try again.')
    await load()
  } finally {
    submitting.value = false
  }
}

onMounted(load)
</script>

<template>
  <main class="storefront-page">
    <header class="storefront-header">
      <RouterLink :to="`/${storeSlug}`" class="storefront-brand storefront-brand-link">
        <span class="storefront-mark">D</span>
        <div><strong>Store</strong><small>Powered by DukaMe</small></div>
      </RouterLink>
      <RouterLink :to="`/${storeSlug}`" class="storefront-cart storefront-cart-link">Continue shopping</RouterLink>
    </header>

    <section class="storefront-cart-page">
      <div v-if="loading" class="storefront-state"><div class="status-spinner" /><p>Loading your cart…</p></div>
      <div v-else-if="order" class="storefront-order-success">
        <div class="storefront-success-icon">✓</div>
        <span class="storefront-eyebrow">Order received</span>
        <h1>Thank you, {{ order.customer_first_name }}.</h1>
        <p>Your order <strong>#{{ order.order_number }}</strong> has been received. The store will contact you on {{ order.customer_phone }}.</p>
        <div class="storefront-success-summary">
          <div><span>Status</span><strong>{{ order.status.name }}</strong></div>
          <div><span>Total</span><strong>{{ money(order.total_minor, order.currency) }}</strong></div>
          <div><span>Items</span><strong>{{ order.items.reduce((sum, item) => sum + item.quantity, 0) }}</strong></div>
        </div>
        <RouterLink :to="`/${storeSlug}`" class="button button-primary button-lg">Continue shopping</RouterLink>
      </div>
      <template v-else-if="cart">
        <div class="storefront-cart-heading">
          <div><RouterLink :to="`/${storeSlug}`" class="storefront-back">← Continue shopping</RouterLink><h1>Your cart</h1><p>{{ itemCountLabel }}</p></div>
        </div>

        <div v-if="error" class="storefront-inline-error">{{ error }}</div>
        <div v-if="cart.items.length" class="storefront-cart-layout">
          <section class="storefront-cart-items">
            <article v-for="item in cart.items" :key="item.public_id" class="storefront-cart-item">
              <RouterLink :to="`/${storeSlug}/products/${item.product_slug}`" class="storefront-cart-item-image"><img v-if="item.image_url" :src="item.image_url" :alt="item.product_name" /><span v-else>No image</span></RouterLink>
              <div class="storefront-cart-item-copy">
                <RouterLink :to="`/${storeSlug}/products/${item.product_slug}`"><strong>{{ item.product_name }}</strong></RouterLink>
                <small v-if="item.variant_label">{{ item.variant_label }}</small>
                <small v-if="item.sku">SKU: {{ item.sku }}</small>
                <div class="storefront-cart-item-bottom">
                  <div class="storefront-quantity"><button type="button" aria-label="Decrease quantity" :disabled="item.quantity <= 1" @click="changeQuantity(item.public_id, item.quantity - 1)">−</button><span>{{ item.quantity }}</span><button type="button" aria-label="Increase quantity" @click="changeQuantity(item.public_id, item.quantity + 1)">+</button></div>
                  <strong>{{ money(item.line_total_minor, item.currency) }}</strong>
                </div>
                <button type="button" class="storefront-remove" @click="remove(item.public_id)">Remove</button>
              </div>
            </article>
          </section>

          <aside class="storefront-checkout-card">
            <div class="storefront-checkout-title"><strong>Checkout</strong><span>{{ itemCountLabel }}</span></div>
            <div class="storefront-order-total"><span>Subtotal</span><strong>{{ money(cart.subtotal_minor, cart.currency) }}</strong></div>
            <p class="storefront-checkout-note">Delivery and payment details will be confirmed by the store.</p>
            <div class="storefront-form-grid">
              <label><span>First name</span><input v-model="form.first_name" autocomplete="given-name" /></label>
              <label><span>Last name</span><input v-model="form.last_name" autocomplete="family-name" /></label>
              <label><span>Phone</span><input v-model="form.phone" type="tel" autocomplete="tel" placeholder="07xx xxx xxx" /></label>
              <label><span>Email <em>Optional</em></span><input v-model="form.email" type="email" autocomplete="email" /></label>
              <label class="storefront-form-full"><span>Order note <em>Optional</em></span><textarea v-model="form.notes" rows="3" placeholder="Anything the store should know?"></textarea></label>
            </div>
            <p v-if="fieldError" class="storefront-form-error">{{ fieldError }}</p>
            <button class="button button-primary button-lg storefront-add" type="button" :disabled="submitting" @click="submitOrder">{{ submitting ? 'Placing order…' : 'Place order' }}</button>
          </aside>
        </div>
        <div v-else class="storefront-empty"><div class="storefront-empty-icon">🛒</div><h2>Your cart is empty</h2><p>Add something you like and it will appear here.</p><RouterLink :to="`/${storeSlug}`" class="button button-primary">Browse products</RouterLink></div>
      </template>
    </section>
  </main>
</template>
