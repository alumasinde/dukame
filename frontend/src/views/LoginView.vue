<script setup lang="ts">
import { ref } from 'vue'
import { RouterLink, useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import { getRequestId } from '../lib/api'

const auth = useAuthStore()
const router = useRouter()
const email = ref('')
const password = ref('')
const showPassword = ref(false)
const error = ref('')
const errorDetails = ref('')

function getErrorMessage(err: any): { message: string; details: string } {
  const code = err?.response?.data?.error?.code
  const message = err?.response?.data?.error?.message
  const requestId = getRequestId(err?.response?.headers || {})

  if (code === 'VALIDATION_ERROR') return { message: 'Please check your email and password.', details: `Request ID: ${requestId}` }
  if (err?.response?.status === 401) return { message: 'Invalid email or password.', details: `Request ID: ${requestId}` }
  if (err?.response?.status === 503) return { message: 'Authentication service is temporarily unavailable.', details: `Request ID: ${requestId}` }
  if (err?.code === 'ECONNABORTED') return { message: 'Connection timeout. Please check your network.', details: `Request ID: ${requestId}` }
  if (!err?.response) return { message: 'Connection failed. Please check your network.', details: `Request ID: ${requestId}` }
  return { message: message || 'Sign in failed. Please try again.', details: `Error: ${code} | Request ID: ${requestId}` }
}

async function submit() {
  if (auth.loading) return
  error.value = ''
  errorDetails.value = ''

  try {
    await auth.login(email.value, password.value)
    await router.replace(auth.onboardingComplete ? '/dashboard' : '/onboarding')
  } catch (err: any) {
    const { message, details } = getErrorMessage(err)
    error.value = message
    errorDetails.value = details
  }
}
</script>

<template>
  <main class="auth-page">
    <div class="auth-brand">
      <span class="brand-mark">D</span>
      <strong>DukaMe</strong>
    </div>

    <section class="auth-card" aria-labelledby="login-title">
      <div class="auth-heading">
        <span class="badge">Merchant workspace</span>
        <h1 id="login-title">Welcome back</h1>
        <p>Sign in to manage your shop, orders and customers.</p>
      </div>

      <div v-if="error" class="alert alert-danger" role="alert">
        <div class="alert-message">{{ error }}</div>
        <div v-if="errorDetails" class="alert-details">{{ errorDetails }}</div>
      </div>

      <form class="form-stack" @submit.prevent="submit">
        <label>
          Email
          <input v-model.trim="email" type="email" autocomplete="email" placeholder="you@example.com" required autofocus />
        </label>

        <label>
          <span class="label-row"><span>Password</span><RouterLink to="/reset-password">Forgot password?</RouterLink></span>
          <span class="password-field">
            <input v-model="password" :type="showPassword ? 'text' : 'password'" autocomplete="current-password" placeholder="Enter your password" required />
            <button type="button" class="password-toggle" :aria-label="showPassword ? 'Hide password' : 'Show password'" @click="showPassword = !showPassword">
              {{ showPassword ? 'Hide' : 'Show' }}
            </button>
          </span>
        </label>

        <button type="submit" class="button button-primary button-block button-lg" :disabled="auth.loading">
          <span v-if="auth.loading" class="button-spinner" aria-hidden="true"></span>
          {{ auth.loading ? 'Signing in…' : 'Sign in' }}
        </button>
      </form>

      <div class="auth-divider"><span>New to DukaMe?</span></div>
      <RouterLink to="/register" class="button button-secondary button-block">Create an account</RouterLink>
      <p class="auth-note">Secure access to your DukaMe merchant workspace.</p>
    </section>
  </main>
</template>

<style scoped>
.alert-details { margin-top: 0.5rem; font-size: 0.875rem; opacity: 0.9; }
</style>
