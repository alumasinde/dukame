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

function getErrorMessage(err: any): string {
  const code = err?.response?.data?.error?.code
  const message = err?.response?.data?.error?.message
  const requestId = getRequestId(err?.response?.headers || {})

  if (import.meta.env.DEV && requestId !== 'unknown') {
    console.error('[DukaMe Auth] Sign-in request failed:', {
      status: err?.response?.status,
      code,
      requestId,
      message,
    })
  }

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
      <strong>DukaMe</strong>
    </div>

    <section class="auth-card" aria-labelledby="login-title">
      <div class="auth-heading">
        <span class="badge">Merchant workspace</span>
        <h1 id="login-title">Welcome back</h1>
        <p>Sign in to manage your shop, orders and customers.</p>
      </div>

      <div v-if="error" class="alert alert-danger" role="alert">
        {{ error }}
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
