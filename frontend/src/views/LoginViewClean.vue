<script setup lang="ts">
import { ref } from 'vue'
import { RouterLink, useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import { getRequestId } from '../lib/api'
import { APP_NAME, APP_TAGLINE } from '../lib/branding'

const auth = useAuthStore()
const router = useRouter()
const email = ref('')
const password = ref('')
const showPassword = ref(false)
const remember = ref(true)
const error = ref('')

function getErrorMessage(err: any): string {
  const code = err?.response?.data?.error?.code
  const message = err?.response?.data?.error?.message
  const requestId = getRequestId(err?.response?.headers || {})
  if (import.meta.env.DEV && requestId !== 'unknown') console.error(`[${APP_NAME} Auth] Sign-in request failed:`, { status: err?.response?.status, code, requestId, message })
  if (code === 'VALIDATION_ERROR') return 'Please check your email and password.'
  if (err?.response?.status === 401) return 'Invalid email or password.'
  if (err?.response?.status === 403) return 'Your account is currently inactive. Please contact support.'
  if (err?.response?.status === 503) return 'Authentication is temporarily unavailable. Please try again.'
  if (err?.code === 'ECONNABORTED') return 'Connection timed out. Please try again.'
  if (!err?.response) return 'Connection failed. Please check your network and try again.'
  return message || 'We could not sign you in right now. Please try again.'
}

async function submit() {
  if (auth.loading) return
  error.value = ''
  try {
    await auth.login(email.value, password.value)
    await router.replace({ name: auth.onboardingComplete ? 'dashboard' : 'onboarding' })
  } catch (err: any) {
    error.value = getErrorMessage(err)
  }
}
</script>

<template>
  <main class="auth-page">
    <header class="auth-brand" :aria-label="APP_NAME">
      <span class="brand-mark">D</span>
      <span class="auth-brand-copy"><strong>{{ APP_NAME }}</strong><span>{{ APP_TAGLINE }}</span></span>
    </header>
    <RouterLink to="/register" class="auth-top-link">Create account</RouterLink>

    <div class="auth-shell">
      <section class="auth-visual" aria-labelledby="login-title">
        <span class="eyebrow">Business login</span>
        <h2 id="login-title">Welcome back</h2>
        <p>Sign in to manage your business, products and orders.</p>
        <div class="auth-benefits">
          <div class="auth-benefit"><span class="auth-benefit-icon"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M4 10h16v10H4zM3 10l2-6h14l2 6M8 14h3"/></svg></span><strong>Manage products</strong><span>Keep your catalogue up to date.</span></div>
          <div class="auth-benefit"><span class="auth-benefit-icon"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M5 6h14l-1 9H7L5 3H2M9 19a1 1 0 1 0 0 .01M17 19a1 1 0 1 0 0 .01"/></svg></span><strong>Track orders</strong><span>Stay on top of every sale.</span></div>
          <div class="auth-benefit"><span class="auth-benefit-icon"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M4 19V9M10 19V5M16 19v-8M22 19H2"/></svg></span><strong>Grow sales</strong><span>Run your store with confidence.</span></div>
        </div>
      </section>

      <section class="auth-card" aria-label="Sign in form">
        <div class="auth-heading">
          <span class="badge">Secure business access</span>
          <h1>Sign in</h1>
          <p>Access your business workspace.</p>
        </div>
        <div v-if="error" class="alert alert-danger auth-alert" role="alert">{{ error }}</div>
        <form class="auth-form" @submit.prevent="submit">
          <label>Email address<input v-model.trim="email" type="email" autocomplete="email" placeholder="you@example.com" required autofocus /></label>
          <label><span class="auth-label-row"><span>Password</span><RouterLink to="/reset-password">Forgot password?</RouterLink></span><span class="auth-password-field"><input v-model="password" :type="showPassword ? 'text' : 'password'" autocomplete="current-password" placeholder="Enter your password" required /><button type="button" class="auth-password-toggle" :aria-label="showPassword ? 'Hide password' : 'Show password'" @click="showPassword = !showPassword">{{ showPassword ? 'Hide' : 'Show' }}</button></span></label>
          <label class="auth-check"><input v-model="remember" type="checkbox" /><span>Remember me</span></label>
          <button type="submit" class="button button-primary auth-submit" :disabled="auth.loading"><span v-if="auth.loading" class="button-spinner" aria-hidden="true"></span>{{ auth.loading ? 'Signing in…' : 'Sign in →' }}</button>
        </form>
        <div class="auth-divider"><span>New to {{ APP_NAME }}?</span></div>
        <RouterLink to="/register" class="button button-secondary auth-secondary">Create a business account</RouterLink>
        <p class="auth-note">Secure access to your {{ APP_NAME }} business workspace.</p>
      </section>
    </div>

    <section class="auth-trust" aria-label="Business platform benefits">
      <div class="auth-trust-item"><span class="auth-trust-icon"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M12 3l8 3v6c0 4.5-3.2 7.8-8 9-4.8-1.2-8-4.5-8-9V6l8-3zM9 12l2 2 4-4"/></svg></span><div><strong>Secure &amp; reliable</strong><small>Your business data is protected.</small></div></div>
      <div class="auth-trust-item"><span class="auth-trust-icon"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M4 17V7h11v10M15 10h3l3 3v4h-6M7 20a2 2 0 1 0 0-4 2 2 0 0 0 0 4M18 20a2 2 0 1 0 0-4 2 2 0 0 0 0 4"/></svg></span><div><strong>Run your store</strong><small>Products, orders and more.</small></div></div>
      <div class="auth-trust-item"><span class="auth-trust-icon"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M4 13v-1a8 8 0 0 1 16 0v1M4 13h3v6H4zM17 13h3v6h-3zM7 19h2"/></svg></span><div><strong>Local support</strong><small>Built for growing businesses.</small></div></div>
    </section>
  </main>
</template>
