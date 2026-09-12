<script setup lang="ts">
import { computed, ref } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'
import { lookupOrder } from '../lib/cart'
import { formatKenyaPhoneDisplay, kenyaPhoneError, normalizeKenyaPhone } from '../lib/phone'
import { APP_MARK, APP_NAME } from '../lib/branding'

const route = useRoute()
const router = useRouter()
const storeSlug = computed(() => String(route.params.storeSlug))
const orderNumber = ref('')
const phone = ref('')
const loading = ref(false)
const error = ref('')
const fieldError = ref('')

const phoneValid = computed(() => !kenyaPhoneError(phone.value))

function extractTrackingToken(trackingUrl: string): string {
  try {
    const path = new URL(trackingUrl, window.location.origin).pathname
    const parts = path.split('/').filter(Boolean)
    return parts[parts.length - 1] || ''
  } catch {
    const parts = trackingUrl.split('/').filter(Boolean)
    return parts[parts.length - 1] || ''
  }
}

async function submit() {
  fieldError.value = ''
  error.value = ''
  if (!orderNumber.value.trim()) {
    fieldError.value = 'Enter your order number (for example ORD-1001).'
    return
  }
  const phoneErr = kenyaPhoneError(phone.value)
  if (phoneErr) {
    fieldError.value = phoneErr
    return
  }
  loading.value = true
  try {
    const response = await lookupOrder(storeSlug.value, {
      order_number: orderNumber.value.trim(),
      phone: normalizeKenyaPhone(phone.value),
    })
    const token = extractTrackingToken(response.data.tracking_url)
    if (!token) {
      error.value = 'We found your order but could not open tracking. Try again shortly.'
      return
    }
    await router.replace({
      name: 'storefront-order-tracking',
      params: { storeSlug: storeSlug.value, trackingToken: token },
    })
  } catch (err: any) {
    const detail = err?.response?.data?.detail
    if (detail?.code === 'store_closed') {
      error.value = detail.message || 'This store is closed.'
    } else {
      error.value =
        typeof detail === 'string'
          ? detail
          : 'We could not find an order with that number and phone. Check and try again.'
    }
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <main class="order-lookup-page">
    <a class="skip-link" href="#order-lookup-form">Skip to form</a>
    <header class="order-tracking-header">
      <RouterLink :to="`/${storeSlug}`" class="storefront-brand storefront-brand-link">
        <span class="storefront-mark" aria-hidden="true">{{ APP_MARK }}</span>
        <div>
          <strong>Track order</strong>
          <small>Powered by {{ APP_NAME }}</small>
        </div>
      </RouterLink>
      <RouterLink :to="`/${storeSlug}`" class="order-tracking-shop">Back to store</RouterLink>
    </header>

    <section class="order-lookup-shell" aria-labelledby="order-lookup-title">
      <div class="order-lookup-card">
        <span class="storefront-eyebrow">Order tracking</span>
        <h1 id="order-lookup-title">Find your order</h1>
        <p>
          Lost the tracking link? Enter the order number from your confirmation SMS or receipt, and the
          phone number used at checkout.
        </p>

        <form id="order-lookup-form" class="order-lookup-form" @submit.prevent="submit">
          <label>
            <span>Order number</span>
            <input
              v-model="orderNumber"
              type="text"
              name="order_number"
              autocomplete="off"
              autocapitalize="characters"
              placeholder="e.g. ORD-1001"
              required
              :disabled="loading"
            />
          </label>
          <label>
            <span>Phone used at checkout</span>
            <input
              v-model="phone"
              type="tel"
              name="phone"
              inputmode="tel"
              autocomplete="tel"
              placeholder="07XX XXX XXX"
              required
              :disabled="loading"
              :aria-invalid="!!phone.trim() && !phoneValid"
              aria-describedby="lookup-phone-hint"
            />
            <p id="lookup-phone-hint" class="storefront-phone-hint" :class="{ ok: phoneValid && phone.trim() }">
              {{
                phone.trim()
                  ? phoneValid
                    ? `Looks good · ${formatKenyaPhoneDisplay(phone)}`
                    : 'Use a Kenyan mobile number such as 07XX XXX XXX'
                  : 'Must match the number on the order.'
              }}
            </p>
          </label>

          <p v-if="fieldError" class="storefront-form-error" role="alert">{{ fieldError }}</p>
          <p v-if="error" class="storefront-form-error" role="alert">{{ error }}</p>

          <button class="button button-primary button-lg button-block" type="submit" :disabled="loading">
            {{ loading ? 'Looking up…' : 'Track order' }}
          </button>
        </form>

        <p class="order-lookup-note">
          For privacy we only show an order when both the number and phone match.
        </p>
      </div>
    </section>
  </main>
</template>
