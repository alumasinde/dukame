<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'
import { lookupOrder } from '../lib/cart'
import { formatKenyaPhoneDisplay, kenyaPhoneError, normalizeKenyaPhone } from '../lib/phone'
import { APP_NAME, APP_MARK } from '../lib/branding'
import { getStorefront } from '../lib/storefront'

const route = useRoute()
const router = useRouter()
const storeSlug = String(route.params.storeSlug)
const storeName = ref('')
const loading = ref(false)
const error = ref('')
const form = reactive({ order_number: '', phone: '' })

const phoneValid = computed(() => !kenyaPhoneError(form.phone))

onMounted(async () => {
  try {
    const res = await getStorefront(storeSlug)
    storeName.value = res.data.name
    document.title = `Track order · ${res.data.name}`
  } catch {
    document.title = 'Track order'
  }
})

async function submit() {
  error.value = ''
  const phoneErr = kenyaPhoneError(form.phone)
  if (!form.order_number.trim()) {
    error.value = 'Enter your order number.'
    return
  }
  if (phoneErr) {
    error.value = phoneErr
    return
  }
  loading.value = true
  try {
    const { data } = await lookupOrder(storeSlug, {
      order_number: form.order_number.trim(),
      phone: normalizeKenyaPhone(form.phone),
    })
    let path = ''
    if (data.tracking_url) {
      try {
        path = new URL(data.tracking_url, window.location.origin).pathname
      } catch {
        path = ''
      }
    }
    if (!path) {
      error.value = 'Order found but tracking link is missing. Contact the store.'
      return
    }
    await router.replace(path)
  } catch (err: any) {
    error.value =
      err?.response?.data?.detail ||
      'We could not find an order with that number and phone. Check and try again.'
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <main class="order-tracking-page order-lookup-page">
    <a class="skip-link" href="#order-lookup-form">Skip to form</a>
    <header class="order-tracking-header">
      <RouterLink :to="`/${storeSlug}`" class="storefront-brand storefront-brand-link">
        <span class="storefront-mark">{{ storeName ? storeName.charAt(0).toUpperCase() : APP_MARK }}</span>
        <div>
          <strong>{{ storeName || 'Store' }}</strong>
          <small>Powered by {{ APP_NAME }}</small>
        </div>
      </RouterLink>
      <RouterLink :to="`/${storeSlug}`" class="order-tracking-shop">Back to shop</RouterLink>
    </header>

    <section id="order-lookup-form" class="order-lookup-shell" tabindex="-1">
      <div class="order-lookup-card">
        <span class="storefront-eyebrow">Order tracking</span>
        <h1>Find your order</h1>
        <p>
          Lost your tracking link? Enter the order number and the phone you used at checkout.
          We will open your live order status page.
        </p>

        <form class="order-lookup-form" @submit.prevent="submit">
          <label>
            <span>Order number</span>
            <input
              v-model="form.order_number"
              type="text"
              autocomplete="off"
              placeholder="e.g. ORD-1042"
              required
            />
          </label>
          <label>
            <span>Phone used at checkout</span>
            <input
              v-model="form.phone"
              type="tel"
              inputmode="tel"
              autocomplete="tel"
              placeholder="07XX XXX XXX"
              required
            />
            <p class="storefront-phone-hint" :class="{ ok: phoneValid && form.phone.trim() }">
              {{
                form.phone.trim()
                  ? phoneValid
                    ? `Looks good · ${formatKenyaPhoneDisplay(form.phone)}`
                    : 'Use a Kenyan mobile number such as 07XX XXX XXX'
                  : 'Must match the number on the order.'
              }}
            </p>
          </label>
          <p v-if="error" class="storefront-form-error" role="alert">{{ error }}</p>
          <button class="button button-primary button-lg button-block" type="submit" :disabled="loading">
            {{ loading ? 'Looking up…' : 'Track order' }}
          </button>
        </form>

        <p class="order-lookup-note">
          Still have the link from checkout or SMS?
          <span>Open that link for the same live updates.</span>
        </p>
      </div>
    </section>
  </main>
</template>
