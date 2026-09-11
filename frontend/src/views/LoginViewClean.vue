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
  if (err?.code === 'ECONNABORTED') return 'Connection timed out. Please check your network and try again.'
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
    <div class="auth-brand">
      <span class="brand-mark">D</span>
      <div><strong>{{ APP_NAME }}</strong><small>{{ APP_TAGLINE }}</small></div>
    </div>

    <section class="auth-card" aria-labelledby="login-title">
      <div class="auth-heading">
        <span class="badge">Business login</span>
        <h1 id="login-title">Welcome back</h1>
        <p>Sign in to manage your business, products and orders.</p>
      </div>

      <div class="auth-benefits" aria-label="DukaMe business features">
        <div class="auth-benefit"><span class="auth-benefit-icon"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M4 10h16M5 10v9h14v-9M7 10V6h10v4M9 19v-5h6v5"/></svg></span><strong>Manage products</strong></div>
        <div class="auth-benefit"><span class="auth-benefit-icon"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M4 5h2l2 11h9l3-8H7M10 20a1 1 0 1 0 0 .01M17 20a1 1 0 1 0 0 .01"/></svg></span><strong>Track orders</strong></div>
        <div class="auth-benefit"><span class="auth-benefit-icon"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M4 19V9M10 19V5M16 19v-8M22 19H2"/></svg></span><strong>Grow sales</strong></div>
      </div>

      <div v-if="error" class="alert alert-danger auth-alert" role="alert">{{ error }}</div>

      <form class="form-stack auth-form" @submit.prevent="submit">
        <label>
          Email address
          <input v-model.trim="email" type="email" autocomplete="email" placeholder="you@example.com" required autofocus />
        </label>
        <label>
          <span class="auth-label-row"><span>Password</span><RouterLink to="/reset-password">Forgot password?</RouterLink></span>
          <span class="auth-password-field">
            <input v-model="password" :type="showPassword ? 'text' : 'password'" autocomplete="current-password" placeholder="Enter your password" required />
            <button type="button" class="auth-password-toggle" :aria-label="showPassword ? 'Hide password' : 'Show password'" @click="showPassword = !showPassword">{{ showPassword ? 'Hide' : 'Show' }}</button>
          </span>
        </label>
        <button type="submit" class="button button-primary button-block button-lg auth-submit" :disabled="auth.loading">
          <span v-if="auth.loading" class="button-spinner" aria-hidden="true"></span>
          {{ auth.loading ? 'Signing in…' : 'Sign in' }}
          <span v-if="!auth.loading" aria-hidden="true">→</span>
        </button>
      </form>

      <div class="auth-divider"><span>New to {{ APP_NAME }}?</span></div>
      <RouterLink to="/register" class="button button-secondary button-block">Create a business account</RouterLink>
      <p class="auth-note">Secure access to your {{ APP_NAME }} business workspace.</p>
    </section>

    <div class="auth-trust">
      <div class="auth-trust-item"><span class="auth-trust-icon"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M12 3l8 3v5c0 5-3.3 8.4-8 10-4.7-1.6-8-5-8-10V6l8-3Z"/><path d="m8.5 12 2.2 2.2 4.8-5"/></svg></span><div><strong>Secure &amp; reliable</strong><small>Your business data is protected</small></div></div>
      <div class="auth-trust-item"><span class="auth-trust-icon"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M3 6h12v10H3zM15 9h3l3 3v4h-6zM7 19a2 2 0 1 0 0-4 2 2 0 0 0 0 4ZM18 19a2 2 0 1 0 0-4 2 2 0 0 0 0 0 0 4Z"/></svg></span><div><strong>Run your store</strong><small>Products, orders and more</small></div></div>
      <div class="auth-trust-item"><span class="auth-trust-icon"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M4 18v-3a8 8 0 0 1 16 0v3M4 18H2v-5h2M20 18h2v-5h-2M7 19h10"/></svg></span><div><strong>Local support</strong><small>Built for growing businesses</small></div></div>
    </div>
  </main>
</template>
